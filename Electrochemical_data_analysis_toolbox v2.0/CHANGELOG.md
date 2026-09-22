# Changelog

All notable changes to the Electrochemical Data Analysis Toolbox are recorded
here. Versions follow semantic versioning (`major.minor.patch`).

## [2.1.1] - 2026-09-22

### Changed

- Moved the polarization (LSV) plot above the Tafel plot with a 1:2 height
  ratio, keeping the highlighted fit region and saved figures in the same layout.

## [2.1.0] - 2026-09-22

### Added

- Added a polarization (LSV) curve beside the toolbox Tafel slope plot, with
  shading for the fitted overpotential region and matching selected Tafel points.
- Added optional minimum/maximum overpotential bounds and an Apply fit range
  button. Regression uses only points inside those bounds; blank bounds retain
  the previous full-range fit. Saved figures include both panels.

## [2.0.3] - 2026-09-22

### Changed

- Made the LSV and EIS left control panels vertically scrollable using a
  scrollbar or mouse wheel, while keeping the plot area fixed.
- Confined wheel handling to the control panels so plot interactions and
  other tool pages retain their own scrolling behavior.

## [2.0.2] - 2026-09-22

### Changed

- Grouped home-screen tools into three columns: individual measurements;
  Data processor, DRTtools, and Folder batch plotter; and reference-electrode
  analysis and experiment procedure.
- Reduced card spacing to accommodate five measurement tools vertically and
  allowed long titles to wrap, preserving separate title and subtitle sizes.

## [2.0.1] - 2026-09-21

### Added

- Added `VERSION.txt` as the visible, authoritative project version.
- Added this changelog and a version-maintenance rule for future changes.
- Added an automated check that the version is valid, displayed by the app,
  and represented in this changelog.

### Changed

- The application title now reads its version from `VERSION.txt` instead of
  embedding the version directly in Python code.

## [2.0.0] - 2026-09-10

### Added

- Added unified individual-file and sample-folder processing.
- Added Origin-ready CSV writers for OCV, LSV, EIS, activation CV, CP, CA,
  and ECSA measurements.
- Added sample-based integration tests and the Ni foil reference dataset.
- Added distinct title and subtitle typography on the toolbox home screen.

### Changed

- Preserved the previous toolbox as v1.0 and introduced the v2.0 folder.
- Corrected the v2 launcher target.

### Preserved

- Reference-electrode analysis, DRTtools, and experiment-procedure behavior.
