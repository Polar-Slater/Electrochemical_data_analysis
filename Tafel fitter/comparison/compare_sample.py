"""Reproducible numerical comparison; leaves both fitters and input unchanged.

Execute the original numerical function bodies in Python 3. Skip the Python 2
interactive/plotting wrappers. Modern SciPy requires an integer bin count and
modern NumPy requires integer slice endpoints (three compatibility casts).
Run fit_engine once per width at the lowest R2; filter its returned candidate
table for each higher threshold. Verify selected results with direct engine calls.
"""
from pathlib import Path
import sys
import json
import csv
import hashlib
import warnings

import numpy as np
import pandas as pd
import scipy.stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE.parent))
from tafel_io import read_datasets, Preparation, prepare
from tafel_core import FitSettings, fit


def original_functions(corrected_index=False):
    folder = ROOT / 'Tafel_Fitter_v1.51'
    engine_text = (folder / 'Tfit_beta1p51.py').read_text(encoding='utf-8')
    plot_text = (folder / 'Tafel_plot_user_v1p1.py').read_text(encoding='utf-8')
    env = dict(np=np, pd=pd, scipy=scipy, stats=scipy.stats, R=8.3145, F=96485, T=293)
    exec((folder / 'common.py').read_text(encoding='utf-8'), env)
    engine = engine_text[engine_text.index('def fit_engine('):engine_text.index('#use to perform quick')]
    if corrected_index:
        engine = engine.replace('counter : counter + index', 'counter : index')
    exec(engine, env)
    exec(engine_text[engine_text.index('def derivative('):engine_text.index('"""General, user-friendly')], env)
    binner = plot_text[plot_text.index('def calc_bin('):plot_text.index('def Plot_fit(')]
    binner = binner.replace('bins=bincount', 'bins=int(bincount)')
    binner = binner.replace('array[ first_index[counter]:first_index[counter+1], 2]',
                            'array[ int(first_index[counter]):int(first_index[counter+1]), 2]')
    binner = binner.replace('array[ first_index[counter]:, 2]', 'array[ int(first_index[counter]):, 2]')
    exec(binner, env)
    return env


def modern_summary(data, settings):
    result = fit(data, settings)
    c = result.best
    return dict(slope_mv=c.slope_mv, i0_a=c.i0_a, j0_ma_cm2=c.i0_a*500,
                start_v=float(data.eta[c.start]), actual_end_v=float(data.eta[c.stop-1]),
                reported_end_v=float(data.eta[c.stop-1]), points=c.stop-c.start,
                width_mv=c.width_mv, actual_width_mv=float(abs(data.eta[c.stop-1]-data.eta[c.start])*1000),
                tafel_r2=c.tafel_r2, lsv_r2=c.lsv_r2, residual=c.residue, threshold=c.threshold,
                minima=len(result.minima), notes=result.notes), result


def legacy_summary(data, env, max_mv=49, corrected_index=False):
    voltage, current = data.eta, data.current_a
    logi = np.log10(np.abs(current))
    # Exact original arange grids for the usual UI entries [0.01,0.05], [0.9,1.0].
    widths = np.arange(0.01, 0.05, 0.001) if max_mv == 49 else np.arange(0.01, 0.051, 0.001)
    thresholds = np.arange(0.9, 1.0, 0.001)
    cache = {}
    for width in widths:
        out = env['fit_engine'](voltage, logi, current, width, 0.9, 1)
        cache[width] = out
    rows = []
    for threshold in thresholds:
        for width in widths:
            out = cache[width]
            if isinstance(out, int):
                continue
            table = out[8].to_numpy()
            allowed = table[(table[:,4] >= threshold) & (table[:,5] >= threshold)]
            if not len(allowed):
                continue
            chosen = allowed[np.argmin(allowed[:,3])]
            start, i0, differential, residual, r2t, r2i, slope = chosen
            rows.append([0, threshold, width, slope, i0, residual, start, r2t, r2i, start+width])
    array = np.array(rows)
    binned = env['binner'](array.copy(), 3, 2, 1)
    bests = binned[2]
    best = bests[0]
    _, threshold, width, slope, i0, residual, start, r2t, r2i, reported_end = best
    direct = env['fit_engine'](voltage, logi, current, width, threshold, 1)
    selected = direct[8].to_numpy()[direct[12]]
    np.testing.assert_allclose(selected[[0,1,3,4,5,6]], [start,i0,residual,r2t,r2i,slope], rtol=1e-12)
    # Reconstruct the actual source slice, including the original indexing behavior.
    cutoff = direct[7]
    vsub = voltage[:cutoff] if cutoff is not None else voltage
    begin = int(np.flatnonzero(vsub == start)[0])
    endpoint = env['approx_index'](start+width, vsub)[0][0]
    stop = min(endpoint if corrected_index else begin+endpoint, len(vsub))
    actual = vsub[begin:stop]
    slope_check = 1000/scipy.stats.linregress(actual, logi[begin:stop]).slope
    np.testing.assert_allclose(slope_check, slope, rtol=1e-12)
    summary = dict(slope_mv=float(slope), i0_a=float(i0), j0_ma_cm2=float(i0*500),
                   start_v=float(start), reported_end_v=float(reported_end), actual_end_v=float(actual[-1]),
                   points=len(actual), width_mv=float(width*1000), actual_width_mv=float(np.ptp(actual)*1000),
                   tafel_r2=float(r2t), lsv_r2=float(r2i), residual=float(residual), threshold=float(threshold),
                   minima=len(rows), cutoff_last_v=float(vsub[-1]),
                   tied_selected_rows=len(bests), distinct_selected_fits=len(np.unique(bests[:,[3,4,6,7,8]], axis=0)),
                   direct_original_engine_verified=True)
    return summary, array


def main():
    path = Path(sys.argv[1]) if len(sys.argv)>1 else Path('d:/Desktop/Sample/Ni foil 2 cm2/Processed/Ni_foil_LSV 2.3 ohm.csv')
    source = read_datasets(path)[0]
    assert source.metadata['area'] == 2
    env = original_functions()
    results = {}
    plotting = {}
    for compensation in (90, 0):
        preparation = Preparation(**{**source.metadata, 'compensation':compensation})
        data = prepare(source, preparation)
        print(f'Running {compensation}% compensation on {len(data.eta)} points', flush=True)
        np.savetxt(HERE/f'github_input_ir{compensation}.csv',
                   np.column_stack([data.eta, data.current_a, np.log10(np.abs(data.current_a))]),
                   delimiter=',', header='Overpotential / V,Current / A,Tafel', comments='')
        modern, modern_result = modern_summary(data, FitSettings())
        legacy, minima = legacy_summary(data, env)
        matched, _ = modern_summary(data, FitSettings(width_max_mv=49, derivative_cutoff=True))
        # Checks of grid/cutoff settings alone, keeping our corrected implementation.
        max49, _ = modern_summary(data, FitSettings(width_max_mv=49))
        results[str(compensation)] = dict(preparation=preparation.__dict__, retained_points=len(data.eta),
                                         modern=modern, github_legacy=legacy,
                                         modern_49mv_with_cutoff=matched, modern_49mv_no_cutoff=max49)
        plotting[compensation] = (data, modern, legacy)
        np.savetxt(HERE/f'github_residual_minima_ir{compensation}.csv',minima,delimiter=',',
                   header='unused,R2 threshold,width V,slope mV per decade,i0 A,residual A per V,start V,Tafel R2,LSV R2,reported end V',comments='')
        with (HERE/f'modern_residual_minima_ir{compensation}.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(modern_result.minima[0].__dict__))
            writer.writeheader()
            writer.writerows(c.__dict__ for c in modern_result.minima)
        print(json.dumps(results[str(compensation)], indent=2), flush=True)
    provenance = dict(source=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      equilibrium_assumed_v=1.23, source_metadata=source.metadata,
                      comparison='Shared positive-current, positive-overpotential data. No manual potential bounds.',
                      python=sys.version, numpy=np.__version__, scipy=scipy.__version__)
    (HERE/'results.json').write_text(json.dumps(dict(provenance=provenance,results=results),indent=2),encoding='utf-8')
    fig, axes = plt.subplots(1,2,figsize=(12,5.3),layout='constrained')
    for ax, compensation in zip(axes,(90,0)):
        data, modern, legacy = plotting[compensation]
        ax.plot(data.log_density,data.eta*1000,color='#9aa4b2',lw=1.4,label='Prepared sample')
        for label,values,color in [('Our fitter',modern,'#1f6feb'),('GitHub v1.51 core',legacy,'#d34e38')]:
            eta=np.linspace(values['start_v'],values['actual_end_v'],100)
            logj=1000/values['slope_mv']*eta+np.log10(values['j0_ma_cm2'])
            ax.plot(logj,eta*1000,color=color,lw=2.5,label=f"{label}: {values['slope_mv']:.2f} mV/dec")
            ax.scatter([logj[0],logj[-1]],[eta[0]*1000,eta[-1]*1000],color=color,s=18)
        ax.set(title=f'{compensation}% iR compensation',xlabel='log10(|j| / mA cm$^{-2}$)',ylabel='Overpotential / mV')
        ax.grid(alpha=0.2)
        ax.legend(loc='upper left',fontsize=9)
    fig.suptitle('Ni foil: same input and preparation; fitted lines span actual regression intervals',fontsize=12)
    fig.savefig(HERE/'comparison.png',dpi=180)
    plt.close(fig)


def diagnostics():
    """Change one behavior at a time for the recorded 90% compensation case."""
    saved = json.loads((HERE/'results.json').read_text(encoding='utf-8'))
    source = read_datasets(saved['provenance']['source'])[0]
    data = prepare(source, Preparation(**source.metadata))
    fixed, _ = legacy_summary(data, original_functions(corrected_index=True), corrected_index=True)
    env = original_functions()
    current = fit(data, FitSettings(width_max_mv=49, derivative_cutoff=True))
    array = np.array([[0,c.threshold,c.width_mv/1000,c.slope_mv,c.i0_a,c.residue,
                       data.eta[c.start],c.tafel_r2,c.lsv_r2,data.eta[c.stop-1]] for c in current.minima])
    binned = env['binner'](array,3,2,1)[2]
    result = {'legacy_with_only_window_index_fixed':fixed,
              'modern_matched_controls_with_legacy_binning_slopes':np.unique(binned[:,3]).tolist()}
    (HERE/'diagnostics.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    if '--diagnostics' in sys.argv:
        diagnostics()
    else:
        main()
