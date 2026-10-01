# Electrochemical data analysis toolbox

The current version is displayed in `VERSION.txt`, and release history is
maintained in `CHANGELOG.md`. Both must be updated whenever the project changes.

Note: The code in this toolbox was generated with assistance from AI.

This GUI opens the existing electrochemical plotting tools from one control panel:

- Open circuit voltage
- Durability
- Experiment procedure
- Reference electrode potential
- ECSA identifier
- LSV Plotter
- EIS Plotter
- EIS to ZView converter
- Folder batch plotter
- Data processor for individual files or complete sample folders

The Data processor writes Origin-ready CSV files to a `Processed` folder. Its
schemas follow the files in `Sample/Ni foil 2 cm2/Processed`: OCV, LSV, EIS,
CV activation, CP/CA durability, and the two ECSA outputs (cycle CV and delta j
versus scan rate). The working area is inferred from a sample folder name such
as `Ni foil 2 cm2`; all settings remain editable before processing. The ECSA
cycle can be selected explicitly, or left blank to use the last available cycle.
LSV output records both the reference-electrode potential and the water-splitting
equilibrium potential together with its iR-compensation settings.
Folder processing skips deposition files named `_it`; they can still be converted
through individual-file processing when needed. Existing matching CSV files are
only replaced after confirmation.

Choose **EIS to ZView**, select one or more CHI EIS `.txt` files, and click
**Convert to ZView**. Select a file in the list to preview its first 500 output
rows (all rows are exported). Use **Browse…** to choose a target folder, or leave
the target blank to save beside each source. Each output is saved as
`<original_name>_ZView.txt`, with no header and three tab-separated columns:
Frequency in Hz, Z' in ohm, and Z'' in ohm. Original signs, row order, and
impedance values are preserved without area normalization. Existing exports
are skipped and reported.

Run `Start Electrochemical Toolbox.bat`, then choose a workflow from the home
screen. Use the Return button on each tool page to go back to the initial page.
