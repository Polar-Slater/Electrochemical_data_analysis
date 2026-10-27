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

### Plot formatting and text

The plot toolbar has **Plot Settings**, **Add Text**, and **Edit Legend** buttons in the OCV,
durability, LSV/Tafel, EIS, CV, ECSA, and folder batch plotting windows.

- Select a panel in Plot Settings, then edit axes, labels/fonts, legends, or
  individual curve styles. **Apply / Preview** updates the figure. Apply changes
  before selecting another panel or curve. Blank paired axis limits enable
  automatic scaling. Tick spacing is in axis units and applies to linear scales.
- **Add Text**, then click inside the plot. Drag an annotation to move it;
  double-click to edit or delete it. Turn off toolbar pan/zoom before placing or
  moving text. Use Unicode Greek characters or Matplotlib math text such as
  `$R_{ct}$` and `cm$^2$`. Plot-area anchoring stays fixed during zoom; data
  anchoring follows the chosen data coordinates.
- **Edit Legend** opens a panel selector and entry list. Select an entry to rename
  it or turn off **Show entry**; use **Move up/down** to reorder entries. Set the
  legend title, font, size, position, columns, frame, and visibility, then click
  **Apply / Preview** before switching panels or closing. Hiding an entry does
  not hide its curve. Edits persist through redraws and exports during the current
  session, mapped by original legend-handle order. Entry edits and legend titles
  are not included in style presets. Reset view clears these edits.
- Export controls specify exact width/height in centimetres, resolution, and
  transparency. **Export figure** supports PNG, TIFF, PDF, and SVG. Existing
  Save plot buttons also use these export settings; ECSA still saves its two
  separate panels, including their styles and annotations.
- Save/load JSON style presets to reuse formatting. Presets exclude annotations,
  axis labels, curve names, and axis limits. Panel and curve styles map by their
  order. Settings and annotations otherwise persist during the current session,
  separately for views with different original titles/axis labels.
- **Reset view** clears the current view's formatting and annotations and
  restores default export settings. The on-screen figure follows window size;
  exact dimensions apply when exporting.

This first version focuses on formatting and text. Insets, arrows, error bars,
and multi-panel layout editing are not included.
# 3D Nyquist plots

In the EIS plotter, choose **3D Nyquist**. X is Z', Y is operating voltage (V),
and the vertical Z axis is -Z''. Voltage is read from the CHI `Init E (V)` header; you can enter or
override it in the operating-voltage field. Missing or nonfinite voltage must
be supplied before plotting. Drag the plot to rotate, then use **Save plot**.

To compare measurements at different voltages, open the **Folder batch plotter**,
select EIS files and choose **3D Nyquist** in EIS options. Each spectrum is drawn
at its own recorded voltage. Files without valid `Init E (V)` are reported and
omitted. Use files measured on the same reference scale: no RHE conversion is
applied. Working area scales only impedance; **Equal axes** applies to Z' and
-Z'', not voltage. The original 2D Nyquist and Bode options remain available.
