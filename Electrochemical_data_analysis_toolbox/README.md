# Electrochemical data analysis toolbox

Note: The code in this toolbox was generated with assistance from AI.

This GUI opens the existing electrochemical plotting tools from one control panel:

- Open circuit voltage
- Durability
- Experiment procedure
- Reference electrode potential
- ECSA identifier
- LSV Plotter
- EIS Plotter
- Kramers–Kronig Validator
- Folder batch plotter

Run `Start Electrochemical Toolbox.bat`, then click a tool to switch to that function inside the same window. Use the Return button on each tool page to go back to the initial page.

The Kramers–Kronig Validator imports CH Instruments EIS text, CSV, TSV, whitespace-delimited TXT, and Gamry-style DTA data. It fits a linear K–K-compliant RC basis, reports normalized residuals and pseudo-χ², and exports measured and fitted values to CSV.
