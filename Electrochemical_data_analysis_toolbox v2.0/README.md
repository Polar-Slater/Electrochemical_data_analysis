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

Run `Start Electrochemical Toolbox.bat`, then choose a workflow from the home
screen. Use the Return button on each tool page to go back to the initial page.
