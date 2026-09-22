"""Descriptive local slopes for the supplied Ni foil LSV; no plateau auto-selection."""
from pathlib import Path
import sys
import csv
import json
import numpy as np
from scipy.stats import linregress
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from tafel_io import read_datasets, prepare, Preparation

source = read_datasets('d:/Desktop/Sample/Ni foil 2 cm2/Processed/Ni_foil_LSV 2.3 ohm.csv')[0]
data = prepare(source, Preparation(**source.metadata))
saved = json.loads((HERE/'results.json').read_text())['results']['90']['modern']
rows = []
for width in [5, 10, 15, 20]:
    for start in range(len(data.eta)):
        target = data.eta[start]+width/1000
        if target > data.eta[-1]+1e-12:
            continue
        stop = np.searchsorted(data.eta, target+1e-12, side='right')
        if stop-start < 5 or data.source_indices[stop-1]-data.source_indices[start] != stop-start-1:
            continue
        x, y = data.log_density[start:stop], data.eta[start:stop]*1000
        if np.ptp(x) == 0:
            continue
        regression = linregress(x,y)
        rows.append([width, float(np.mean(y)/1000), float(np.mean(data.density[start:stop])),
                     regression.slope, regression.rvalue**2, stop-start, float(y[0]/1000), float(y[-1]/1000)])
array = np.array(rows)
with (HERE/'local_slopes.csv').open('w',newline='',encoding='utf-8') as stream:
    writer=csv.writer(stream)
    writer.writerow(['window_mV','mean_eta_V','mean_j_mA_cm2','slope_mV_dec','R2','points','start_eta_V','end_eta_V'])
    writer.writerows(rows)
fig,axes=plt.subplots(1,2,figsize=(11.5,4.5),layout='constrained')
for width in [5,10,15,20]:
    values=array[(array[:,0]==width)&(array[:,1]>=0.28)]
    axes[0].plot(values[:,1],values[:,3],lw=1.2,label=f'{width} mV windows')
    axes[1].plot(values[:,2],values[:,3],lw=1.2,label=f'{width} mV windows')
axes[0].axvspan(saved['start_v'],saved['actual_end_v'],color='grey',alpha=.15,label='Automated fit interval')
for ax in axes:
    ax.axhline(saved['slope_mv'],color='black',lw=1,ls='--',label='Automated result: 60.14')
    ax.set(ylabel='Local Tafel slope / mV decade$^{-1}$',ylim=(30,130))
    ax.grid(alpha=.2)
axes[0].set(xlabel='Mean overpotential / V',xlim=(.28,.44))
axes[1].set(xlabel='Mean j / mA cm$^{-2}$',xscale='log')
axes[0].legend(fontsize=8)
fig.suptitle('Ni foil local-slope diagnostic: 90% iR correction; rising branch shown (eta >= 0.28 V)')
fig.savefig(HERE/'local_slope_check.png',dpi=180)
plt.close(fig)
for lo,hi in [(.30,.32),(.34,.36),(.36,.38),(.40,.42)]:
    values=array[(array[:,0]==10)&(array[:,1]>=lo)&(array[:,1]<=hi),3]
    print(f'10 mV windows, mean eta {lo:.2f}-{hi:.2f} V: median {np.median(values):.3f}, range {min(values):.3f}-{max(values):.3f} mV/dec')
mask=(data.eta>=saved['start_v']-1e-12)&(data.eta<=saved['actual_end_v']+1e-12)
print('Selected j range:',data.density[mask][[0,-1]])
print('Selected log current span:',np.ptp(data.log_density[mask]),'decades')
