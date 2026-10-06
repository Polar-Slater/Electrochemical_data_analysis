# EIS Analysis

A standalone EIS application based on DearEIS 5.1.3, with simpler loading for
the electrochemical toolbox's CHI files. The application version is in VERSION.txt
and appears in the window title, Home screen, and About dialog.

## Open the application

On this computer, double-click **Open EIS Analysis.bat**. It uses the existing
`.venv-deareis` environment beside this folder. No installation is needed again.

In VS Code:

1. Use **File > Open Folder** and select this **EIS Analysis** folder.
2. Open **launch.py**.
3. Click **Run Python File**, or press F5 and select **Open EIS Analysis**.

VS Code needs its Python extension and a Python interpreter selected. The launcher
automatically uses this folder's `.venv` if present, otherwise the existing sibling
`.venv-deareis`. On a different computer, install Python 3.11 or newer (initial build
tested with Python 3.14 on Windows) and run **Setup.bat** once. An internet connection
is needed for setup. The app includes its DearEIS source; do not pip-install this folder.

## Load and analyze

1. Click **Open EIS files** on Home or in the File menu.
2. Select one or more files using the normal Windows file picker.
3. A working project is created automatically if none is active. Additional files
   are added to the active project.
4. Select a dataset, then use **Fitting**, **DRT**, **Kramers-Kronig**, or **Z-HIT**.
5. Use DearEIS's existing project saving and plot/result export controls.

## Enter initial fitting values (0.2.0)

On **Fitting**, enter your circuit and press Enter. The **Initial parameters**
table above the plots immediately lists its components. Edit **Initial value**,
**Minimum**, **Maximum**, and **Fixed** directly. Scientific notation such as
`1.58e-3` is accepted; use `inf` or `-inf` for unlimited bounds.

Click **Apply initial values**, or simply click **Perform** to apply the entries
and fit. Invalid numbers or values outside their bounds are explained beside the
table and block the fit. The separate results table on the left continues to show
the selected fit's parameters. **Apply fitted values as initial values** refreshes
the editable table for another fit. The graphical editor remains available under
**Edit**, and the diagram is in the adjacent **Fitted circuit** tab.

## Save a project (0.2.0)

**File > Save project** opens the standard Windows Save dialog for a new project.
Choose a folder and filename; `.json` is supplied automatically. Subsequent Save
operations use that project's existing path. **Save project as** opens the dialog
again, with overwrite confirmation. Cancel leaves the project open and unchanged.
New projects remember the last successfully used save folder across restarts.
Saving an existing project under a different name retains DearEIS's behavior of
opening the saved copy as another project tab.

The analysis settings, circuit editor, plots, project format and result exports
are inherited from DearEIS. This application does not change fitting or DRT solvers.
Use File > New project when you want a separate group of datasets.

## Accepted text inputs

- Raw CHI `.txt` exports: metadata followed by `Freq/Hz, Z'/ohm, Z"/ohm, ...`.
- Extracted tables with frequency, real and imaginary impedance headers.
- Toolbox processed CSV, including a separate Origin-style units row.
- Headerless, three-column text/CSV: frequency in Hz, Z' in ohms, signed Z'' in ohms.
  Commas, tabs and whitespace are supported.
- Other file extensions are passed to the original pyimpspec parsers.

Headers explicitly marked `-Z''` are converted back to signed Z''. Area-normalized
`ohm cm2` values are divided by the positive working area recorded in the file,
so analysis and existing exports continue to use ohms. If area is missing, open
the original raw file. Headerless input always means signed Z'', not -Z''.
Frequency must be Hz. Invalid values, repeated frequencies and malformed rows
produce an error instead of silently dropping or averaging measurements.
Files are sorted by descending frequency; original input files are never rewritten.

## Storage and maintenance

Settings, recent projects and recovery snapshots are stored under `.user-data/`
inside this folder, independently of the original DearEIS installation. Save your
projects explicitly to a chosen location. The toolbox itself is unchanged; a future
toolbox button can launch this folder's `launch.py` in a separate process.

Update VERSION.txt and CHANGELOG.md for every release. Custom code lives in
`eis_app/`; the adapted DearEIS source lives in `src/deareis/`. See UPSTREAM.md
for provenance and modified upstream files. DearEIS's own version remains 5.1.3.

Run automated checks from this folder:

```powershell
..\.venv-deareis\Scripts\python.exe -m unittest discover -s tests -v
```

For a local setup, replace that interpreter with `.venv\Scripts\python.exe`.

Initial validation: automated checks cover imaginary-sign conversion, electrode-area
conversion, invalid input rejection, the workspace's Ni-foil raw/processed agreement,
synthetic RC fitting and DRT, and project serialization. A separate GUI smoke check
(`tests/gui_smoke.py`) verifies startup, canceled selection, automatic project
creation, repeat imports, dataset selection, and rendered Nyquist plots. It supplies
file-picker results programmatically; manual native-dialog interaction and every
upstream analysis option have not been exhaustively tested.

Version 0.2.0 adds tests for parameter validation, fixed values and bounds during
fitting of the SS310 sample, and native save-dialog options. The GUI check imports
all 11 raw EIS files in the workspace Sample folder and tests table editing,
fitted-value reuse, canceled saving, saving/overwriting/copying, and project reopening.
Test project files are written only to a temporary directory; sample files and
existing user projects are not rewritten.

## License

GPL-3.0-or-later, retaining DearEIS's copyright and license notices. See LICENSE,
COPYRIGHT, CONTRIBUTORS, and the bundled licenses in src/deareis.
