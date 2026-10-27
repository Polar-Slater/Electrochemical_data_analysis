# Changelog

All notable changes to the Electrochemical Data Analysis Toolbox are recorded
here. Versions follow semantic versioning (`major.minor.patch`).

## [2.6.1] - 2026-10-26

### Changed

- Place -Z'' on the vertical (Z) axis in both 3D Nyquist views, with Z' on X
  and operating voltage on Y. Equal impedance scaling now applies to XZ.

## [2.6.0] - 2026-10-26

### Added

- Added rotatable 3D Nyquist plots to the EIS and folder batch plotters with
  Z', -Z'', and operating voltage axes. Voltage comes from CHI Init E (V)
  on the recorded reference scale; the single-file plotter permits manual entry.
- Report files without valid operating voltage when building a 3D comparison.
  Working-area normalization affects only impedance; equal axes applies to XY.

## [2.5.0] - 2026-10-20

### Added

- Added an Edit Legend toolbar button in all plotting windows. Rename, reorder,
  or hide individual legend entries without modifying curves, and edit the
  legend title, font, size, position, columns, frame, and visibility.
- Preserve legend edits across redraws and figure exports, including separate
  ECSA panels. Legend entries map to their original handle order in each view.

## [2.4.1] - 2026-10-20

### Changed

- Default plot fonts to Times New Roman, including titles, axes, tick labels,
  legends, math text, and new annotations. Custom font settings remain available.
- Apply the selected plot font family to legend entries as well.

## [2.4.0] - 2026-10-20

### Added

- Shared Plot Settings for OCV, durability, LSV/Tafel, EIS, CV, ECSA, and
  folder batch previews: axes, ticks, fonts, curve styles, legends, style presets,
  and exact-size PNG/TIFF/PDF/SVG export.
- Click-to-place text annotations with drag, double-click editing, deletion,
  font styling, rotation, and data or plot-area anchoring. Annotations survive
  redraws and appear in exports, including separate ECSA panel exports.

## [2.3.2] - 2026-10-01

### Changed

- Entering the DRTtools page no longer launches the application automatically.
  Click Open DRTtools on the page to launch it.

## [2.3.1] - 2026-09-24

### Changed

- Matched the ZView converter to the plotting tools with a scrollable left
  control panel, top Return button, green file-selection action, and a full-height
  preview on the right. Added Clear and a compact scrollable file list.

## [2.3.0] - 2026-09-24

### Added

- Added a selected-file ZView output preview showing up to 500 rows, with
  shared validation between preview and export. Exports still contain all rows.
- Added a target-folder picker for ZView conversion; leaving it blank saves
  beside each source. Existing exports remain protected from replacement.

## [2.2.0] - 2026-09-24

### Added

- Added an EIS to ZView tool for converting selected CHI EIS text files to
  headerless, tab-separated Frequency (Hz), Z' (ohm), and Z'' (ohm) data.
  Exports preserve impedance signs and row order and are saved beside each
  source with the `_ZView.txt` suffix. Existing exports are skipped.

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
