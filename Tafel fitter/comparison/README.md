# Ni foil: our fitter versus GitHub Tafel_Fitter v1.51

Comparison performed 2026-09-18 using the supplied file:
`D:/Desktop/Sample/Ni foil 2 cm2/Processed/Ni_foil_LSV 2.3 ohm.csv`.
Both applications and the source data were left unchanged.

## Main result: the CSV's recorded 90% iR compensation

| Quantity | Our fitter | Original GitHub numerical logic |
| --- | ---: | ---: |
| Tafel slope (mV/decade) | 60.1369 | 89.8991 |
| Exchange current i0 (A) | 2.70792e-9 | 3.66541e-7 |
| Exchange current density j0 (mA/cm2) | 1.35396e-6 | 1.83270e-4 |
| Actual fitted overpotential (V) | 0.361326–0.376751 | 0.386663–0.437174 |
| Points in regression | 21 | 90 |
| Requested window width (mV) | 16 | 42 (one of repeated nominal-width selections) |
| Actual regression width (mV) | 15.4253 | 50.5104 |
| Tafel R2 | 0.999685 | 0.996135 |
| LSV R2 | 0.996019 | 0.989240 |
| Physical residual (A/V) | 0.143188 | 0.371384 |

The original code returns repeated selections of the same underlying regression
at different nominal window settings. The table uses the first selected row.
Its **reported** endpoint is 0.428663 V, while its actual regression extends to
0.437174 V. These are different because of the indexing behavior below.
The exchange currents are extrapolated fit parameters; differing slopes and
regions substantially change their intercepts. Higher R2 alone does not prove
physical validity.

## Controlled preparation

- Area: 2 cm2; reference offset: 0.929 V vs. RHE; resistance: 2.3 ohm.
- Equilibrium potential: assumed 1.23 V vs. RHE, consistent with our OER workflow;
  the supplied CSV does not record it.
- E_corrected = E_original + 0.929 - I_A * 2.3 * compensation/100.
- eta = E_corrected - 1.23; j = I_A * 1000 / 2.
- Rebuilt from the supplied original potential/current columns. Reconstructed
  corrected potentials match the exported column within 5.1e-10 V; current
  densities match within 5.1e-8 mA/cm2 (CSV precision).
- Both algorithms receive identical 464 positive-current, positive-overpotential
  points out of 800. No manual overpotential limits or positive minimum-|j|
  cutoff is imposed. The original is given eta, I in A, log10(|I|).
- T = 293 K; n = 1; nominal slope bin size 1 mV/decade.
- R2 thresholds 0.900 through 0.999 in 0.001 steps.
- Our default widths: 10 through 50 mV, 1 mV steps; derivative cutoff off.
- Original UI-style inputs [0.01,0.05] produce widths 10 through 49 mV because
  its upper endpoint is excluded; its 15th-order derivative cutoff is always on.

Repeating our fit with a 49 mV maximum AND derivative cutoff enabled leaves our
selected slope unchanged: 60.1369 mV/decade. These setting differences therefore
do not account for the main difference on this sample.

## Why the outputs differ

The original `fit_engine` computes `index` as an absolute array index near the
intended endpoint, but slices `voltage_sub[counter : counter + index]`.
Adding the start index again makes the regression interval too long and can
make many nominal widths select the same tail of the data. Its reported interval
is nevertheless only `start + requested_width`.

A controlled diagnostic replacing only those slices with
`voltage_sub[counter : index]` (and corresponding current/log-current slices)
changes the original result from **89.8991 to 60.8760 mV/decade**. Its actual
regression then spans 0.362134–0.378232 V, using 22 points. The rest of its
fitting and binning logic remains unchanged. Thus the window-index issue explains
most of this sample's difference.

Our code also uses inclusive sampled endpoints, fixed bins anchored to zero,
correct last-bin handling, a minimum point count, positive-slope eligibility,
scaled polynomial fitting and more precise physical constants. The original
uses nearest-endpoint/exclusive slicing and range-dependent bin edges. Applying
the original binning to our matched-control candidate minima selects
60.4204 mV/decade, illustrating additional binning sensitivity. This is a separate
diagnostic, not the main output from either tool.

The different placement of n in the old residual formula does not affect this
comparison because n = 1.

## Comparison with the earlier 0% screenshot

| Quantity | Our fitter, 0% iR | Original numerical logic, 0% iR |
| --- | ---: | ---: |
| Tafel slope (mV/decade) | 60.8295 | 186.8637 |
| i0 (A) | 2.61809e-9 | 6.25860e-5 |
| Actual overpotential range (V) | 0.349–0.360 | 0.434–0.489 |
| Points | 12 | 56 |
| Tafel R2 | 0.999688 | 0.996124 |
| LSV R2 | 0.998201 | 0.999295 |

Our 0% result reproduces the earlier screenshot's 60.83 mV/decade. The new CSV
records 90% compensation, so the 90% row is the primary comparison. These runs
establish software behavior; they do not independently validate a kinetic region
or reaction mechanism.

## Execution and compatibility details

The local `Tfit_beta1p51.py`, `Tafel_plot_user_v1p1.py` and `common.py` were
verified against the [GitHub Windows v1.51 archive](https://github.com/MEG-LBNL/Tafel_Fitter)
and match after CRLF normalization. SHA-256 values are recorded in results.json.

This is an execution of the original numerical function bodies under Python 3,
not an unmodified Python 2 GUI run. The harness bypasses Python 2 print/input and
per-fit file/plot wrappers. For current SciPy/NumPy, it casts the bin count to int
(truncating the original float) and casts two NumPy-derived slice endpoints to
int. Original numerical/window/binning behavior otherwise remains intact for
the baseline. Historical dependency versions could affect binning details.

The original engine is run once per width at R2 >= 0.900 and its full candidate
table reused for higher thresholds; candidate regressions do not depend on the
threshold. The selected baseline results are verified with direct original
engine calls at the selected width/threshold. Actual regression endpoints and
slopes are independently reconstructed and checked with SciPy regressions.

Run from the project root (requires NumPy, SciPy, pandas and Matplotlib):

```powershell
python "Tafel fitter/comparison/compare_sample.py"
python "Tafel fitter/comparison/compare_sample.py" --diagnostics
```

The source file can be supplied as the first positional argument for the main
run; this script is specifically configured for this 2 cm2 sample.

## Saved outputs

- `comparison.png`: fitted-line comparison over the actual regression intervals.
- `results.json`: settings and full numerical outputs for both compensation cases.
- `diagnostics.json`: index-only correction and original-binning diagnostic.
- `github_input_ir*.csv`: shared prepared three-column inputs for the original.
- `github_residual_minima_ir*.csv`: original residual-minimized candidate tables.
- `modern_residual_minima_ir*.csv`: our corresponding candidate tables.
- `compare_sample.py`: reproducible numerical harness.

Original method: Peter Agbo and Nemanja Danilovic, *An Algorithm for the
Extraction of Tafel Slopes*, J. Phys. Chem. C 2019, 123, 30252–30264,
[DOI 10.1021/acs.jpcc.9b06820](https://doi.org/10.1021/acs.jpcc.9b06820).
