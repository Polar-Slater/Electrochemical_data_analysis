# Changelog

## 0.2.0 - 2026-10-04

- Added an Initial parameters table on the Fitting tab, available before the first fit.
- Added direct editing of initial values, bounds, and fixed flags, with scientific
  notation and validation. Perform applies edits automatically.
- Kept the circuit diagram in an adjacent Fitted circuit tab and synchronized the
  table with circuit edits and Apply fitted values as initial values.
- Replaced the project Save/Save As browser with the native Windows dialog,
  including filename suggestions, JSON extension, and overwrite confirmation.
- Remember the last successful save folder across application restarts.
- Preserve the existing project identity if Save As is canceled or fails.

## 0.1.0 - 2026-10-03

- Created a standalone EIS Analysis application based on DearEIS 5.1.3.
- Added a VS Code launch configuration, launch.py, and Windows launch/setup scripts.
- Added a version file used by the title, Home screen, and About dialog.
- Added native multi-file selection and automatic project creation on first import.
- Added toolbox-compatible CHI and processed CSV imports with explicit imaginary
  sign and electrode-area conversion, preserving impedance in ohms.
- Isolated settings and recovery state from the original DearEIS application.
- Retained upstream analysis, plotting, project serialization and result exports.
