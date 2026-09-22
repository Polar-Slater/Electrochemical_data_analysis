# Changelog

Versions here refer to this project's standalone adaptation, not the upstream
MEG-LBNL Tafel_Fitter v1.51. Each change to this tool must update the version and
this log together. Dates use YYYY-MM-DD.

## 1.0.0 — 2026-09-21

First versioned release of the existing standalone fitter.

### Added

- Central version in `tafel_version.py`, displayed in the window title, application
  header and Credits dialog.
- Software version recorded in `settings_and_results.json`, `tafel_data.csv` and
  `fit_summary.csv` so exported analyses identify the software used.
- This changelog and scoped maintenance instructions requiring future version
  and changelog updates together.

### Existing features included in this baseline

- Standalone Python 3/Tkinter GUI with preview, asynchronous fitting, cancellation,
  plots and export; not yet integrated into the toolbox.
- Project CHI/CSV data readers, preparation controls and support for original
  fitter example inputs.
- Adaptation of the original automatic window-selection method with corrected
  window indexing, input validation and numerical implementation changes
  documented in the README.
- Original software and research attribution in the GUI and README.
- Sample comparison scripts, results and local-slope diagnostics in `comparison/`.

Earlier work was unversioned. This release adds version tracking without changing
the fitting algorithm. Proposed plateau-selection and interpretation improvements
are not implemented in this release.
