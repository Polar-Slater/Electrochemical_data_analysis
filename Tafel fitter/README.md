# Tafel fitter

Current project version: **1.0.0**. See [CHANGELOG.md](CHANGELOG.md) for release
history. This version is independent of the original MEG-LBNL fitter's v1.51.

Standalone Python 3 desktop application adapted from the MEG-LBNL
Tafel_Fitter v1.51 method for this electrochemical analysis project. It uses
Tkinter and Matplotlib, like toolbox v2.0, but is not yet integrated into the
toolbox. The original fitter and both toolbox versions are unchanged.

## Credits

Original fitting software: **Peter Agbo**, [MEG-LBNL Tafel_Fitter v1.51](https://github.com/MEG-LBNL/Tafel_Fitter),
Lawrence Berkeley National Laboratory.

Fitting methodology: **Peter Agbo and Nemanja Danilovic**, *An Algorithm for the
Extraction of Tafel Slopes*, J. Phys. Chem. C 2019, 123, 30252–30264.
[DOI: 10.1021/acs.jpcc.9b06820](https://doi.org/10.1021/acs.jpcc.9b06820).

This project's Python 3 GUI, data-format adaptation and implementation corrections
were developed with AI assistance. Differences from the original implementation
are documented below. The GUI includes a permanent attribution and a **Credits**
button with links to the original project and paper.

## Start

Double-click **Start Tafel Fitter.bat**, or run from this folder:

```powershell
python tafel_gui.py
```

Dependencies: Python 3.10 or newer with Tkinter, NumPy and Matplotlib.
If needed, install the Python packages with:

```powershell
python -m pip install -r requirements.txt
```

## Accepted project data

| Input | Handling |
| --- | --- |
| CHI LSV `.txt` | Reads `Potential/V, Current/A` after the instrument metadata. |
| Toolbox processed LSV `.csv` | Supports both `Processed` Origin-style CSVs with a units row and older `Processed data/*_processed.csv` files. Reads **Original Potential** and **Original Current**; converts mA to A. |
| Toolbox Tafel `.csv` | Reads `Overpotential (V)` and `Current density (mA/cm²)` or the `cm^2` spelling. Recomputes log10 of the magnitude; does not apply corrections again. |
| Original v1.51 example `.csv` | Reads overpotential and current in A, including the bundled Ir OER baseline-adjusted column. Recomputes the logarithm from the current. |

Metadata includes reference offset, equilibrium potential, working area, solution
resistance and compensation percentage. Area can also be inferred from a parent
folder such as `Ni foil 2 cm2`, and resistance from a name such as `2.3 ohm`.
Missing values remain visible defaults for the user to review; resistance inferred
from a filename does not enable compensation automatically.

Combined toolbox exports are separated using their `File` column. You can open
multiple files and select one dataset at a time. Fitting and settings apply to
the selected dataset; switching datasets reloads its metadata.

For raw/original data, the transformation matches the toolbox:

```text
E_corrected_vs_RHE = E_original + E_reference - I_A * Rs * compensation_percent / 100
eta_V = E_corrected_vs_RHE - E_equilibrium
j_mA_cm2 = I_A * 1000 / area_cm2
```

LSV CSVs are rebuilt from original E/I and their metadata to avoid compounding
the already-exported iR correction. Tafel CSVs use the exported eta directly;
reference, equilibrium and resistance controls are disabled for these files.
For density input, area is used to recover total current; changing it does not
rescale the supplied density. Unknown equilibrium potentials are left blank in
exported corrected-potential columns rather than invented.

## Workflow

1. Open an LSV TXT or supported CSV. Verify area, reference potential, equilibrium
   potential and compensation. Defaults are **not** a determination of your
   experimental reference electrode. OER commonly uses equilibrium 1.23 V vs.
   RHE and HER uses 0 V vs. RHE.
2. Choose Anodic or Cathodic. The fitter requires current and overpotential to
   have the corresponding sign and excludes zero current before taking logs.
3. Preview the curve. Optionally set signed minimum/maximum overpotential and
   minimum current-density magnitude to restrict the candidate kinetic region.
   For example, cathodic bounds might be -0.15 to -0.02 V.
4. Review fitting settings, then run the automatic fit. Computation runs in a
   background thread and can be cancelled. Changing settings during a run makes
   its result ineligible for display/export.
5. Inspect the selected region, Tafel line, derivative and stability plot.
6. Export to a new timestamped folder inside a directory you choose.

The Ni-foil processed sample can be exercised with its recorded area 2 cm²,
reference 0.929 V, resistance 2.3 ohm and 90% compensation, equilibrium 1.23 V,
and an illustrative overpotential range 0.28–0.43 V. This is a software example,
not a validation of the sample's reaction mechanism or of that region's kinetics.

## Fitting method and differences from v1.51

Based on Peter Agbo and Nemanja Danilovic, **An Algorithm for the Extraction of
Tafel Slopes**, J. Phys. Chem. C 2019, 123, 30252–30264.
DOI: https://doi.org/10.1021/acs.jpcc.9b06820
Original project: https://github.com/MEG-LBNL/Tafel_Fitter
Local reference implementation: `../Tafel_Fitter_v1.51/`.

For each requested window width, the engine slides a window across the selected
single sweep. It regresses log10(|I|) and |I| against |eta|, requiring positive
slopes and sufficient R² for **both** regressions. For each width/R²-threshold
pair, it keeps the fit minimizing:

```text
abs(d|I|/d|eta| - i0 * n * F / (R * T))
```

The retained slopes are grouped into fixed-width magnitude bins. The winning
bin spans the most distinct requested window widths; the final fit has the
highest Tafel R² in the winning bin(s), with deterministic LSV R², residual and
width tie-breaks. Cathodic slopes are reported as negative, with their magnitude
also shown. i0 is in A and j0 is in mA/cm².

Changes from the historical implementation:

- Python 3, reusable reader/engine/GUI modules, portable paths, no interactive
  Python `input()` evaluation, no SciPy or pandas dependency.
- Correct window endpoints: inclusive acquired endpoints are used consistently
  by regressions, plots, range reporting and exports. The old code added an
  absolute end index to the start index.
- Both parameter grids include the upper bound when it lies on the step grid.
  Requested and actual sampled window widths are exported separately.
- Correct electron-number placement follows equation 2b of the paper (`n` in
  the numerator). v1.51 placed it in the denominator; n=1 is unchanged.
- The selected polynomial order controls the actual derivative fit. The
  polynomial is fitted in a scaled coordinate system for numerical conditioning.
- Derivative-based truncation is **optional and off by default**. A maximum
  caused by a redox peak or noise does not necessarily mark mass transport.
  Preview it before enabling. The fit excludes points beyond the maximum.
- Fixed slope bins anchored to zero replace data-range-dependent bin edges;
  last-bin entries are retained. Tiny numerical jitter at bin edges is rounded.
- Rejects non-finite/malformed input and folded or duplicate selected potentials;
  it does not combine CV forward/reverse sweeps. Windows cannot bridge excluded
  points. Five points per fit are required by default.

Consequently, results need not reproduce the original implementation's numbers
exactly. The physical residual is a low-overpotential Butler–Volmer consistency
criterion, not proof that an arbitrary region is kinetically controlled. Inspect
the data and settings. Fits remain sensitive to reference/equilibrium choices,
iR correction, fit range, thresholds and bin width. Window steps should be
appropriate to the acquired potential resolution. A single-width winning bin
does not establish window-width stability. No mechanistic assignment or
statistical confidence interval is inferred automatically.

## Exported files

- `tafel_data.csv`: toolbox Tafel column names, metadata, current density,
  log-current density, overpotential and selected-fit membership.
- `fit_summary.csv`: selected slope, i0, j0, potential bounds, point count, R²
  values, residual and requested/actual window widths; labels and units rows.
- `residual_minima.csv`: best candidate for every successful width/threshold pair.
- `settings_and_results.json`: input identity, original metadata, preparation,
  search settings, selected candidate and diagnostic notes.
- `tafel_fit.png`: four-panel diagnostic figure.

CSV files use UTF-8 with BOM for Excel/Origin compatibility. Exports get new
folders and do not overwrite input files. The CSVs are not generic instrument
importers; unsupported schemas receive a clear error.

## Validation and future integration

From the project root:

```powershell
python -m unittest discover -s "Tafel fitter/tests" -v
```

Tests cover known anodic/cathodic slopes and exchange currents, current/area/iR
units, non-unit electron number, derivative cutoff, cancellation, invalid inputs,
the Ni-foil project formats, all seven original example curves, combined-file
separation, export round-trip and a real Tk asynchronous fitting workflow.

`tafel_io.py`, `tafel_core.py` and `tafel_output.py` have no GUI dependency.
`TafelApp(master, on_return=None)` is a reusable Tk frame for later toolbox
integration. No toolbox launcher or existing project source was modified.
