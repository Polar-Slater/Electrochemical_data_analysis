# Folder batch plotter

Import one folder of electrochemical data files and plot grouped measurements.

Preferred filename pattern:

```text
sample_measurement_suffix.txt
```

Measurements recognized:

- `OCV`
- `LCV` or `LSV`
- `EIS`
- `CP`
- `CV`

ECSA uses only CV files with scan-rate labels such as `10 mV`, `20 mV`, or `100 mV`, and defaults to the last cycle. It excludes files such as `CV active` or generic `CV scan` files.

CV active uses only CV files whose names or suffixes say `active` or `activation`.

LSV can apply reference-electrode conversion, iR compensation, and Tafel plotting. The GUI auto-fills one Rs value per file from filename text such as `2.60 ohm`, and the compensation level box applies the same percentage to every loaded LSV file. The reference electrode box adds a V offset to plot vs. RHE, and Tafel mode uses the equilibrium potential plus working area to plot overpotential vs. `log10(|j| / mA cm^-2)`. The Tafel overpotential range fields limit both the displayed points and fitted slope.

EIS includes the toolbox plot controls for Nyquist/Bode, frequency axis, Bode Y axis, points, connected lines, equal axes, and working-area impedance normalization.

The left control panel is scrollable so all plot-specific settings remain reachable.

OCV and CP support Y-axis ranges. CP also uses the reference-electrode offset, working area current-density summary, and CP-specific iR compensation controls.

Extra suffix text remains visible in the file list and plot legends through the full filename stem.

If a filename does not contain a measurement token, the scanner reads the second line of the text file and recognizes common CHI measurement names such as `Cyclic Voltammetry`, `Linear Sweep Voltammetry`, `Open Circuit Potential - Time`, `Multi-Current Steps`, and `Chronopotentiometry`.
