"""Run on a desktop to check the migrated K-K workflow end to end."""
import csv
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

import numpy as np

TOOLBOX = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLBOX))

import electrochemical_toolbox as toolbox
from kramers_kronig_gui import KKPlotApp


def main():
    app = toolbox.ElectrochemicalToolbox()
    app.withdraw()
    errors = []
    app.report_callback_exception = lambda *args: errors.append(args)
    try:
        tool = next(tool for tool in toolbox.TOOLS if tool.page_factory is KKPlotApp)
        assert any(tool.title in column for column in toolbox.HOME_COLUMNS)
        app.show_tool(tool)
        page = app.active_page
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "rc_spectrum.csv"
            target = Path(directory) / "kk_results.csv"
            frequency = np.logspace(5, -2, 80)
            # Two RC terms at the fitted basis endpoints give an exact reference.
            omega = 2 * np.pi * frequency
            impedance = 5 + 30 / (1 + 1j * omega / omega.max()) + 100 / (1 + 1j * omega / omega.min())
            page.max_rc.set(2)
            page.include_capacitance.set(False)
            np.savetxt(source, np.column_stack((frequency, impedance.real, impedance.imag)),
                       delimiter=",", header="frequency,zreal,zimag", comments="")
            with patch("kramers_kronig_gui.filedialog.askopenfilename", return_value=str(source)), \
                 patch("kramers_kronig_gui.messagebox.showerror") as error:
                page.load_file()
                page.run_test()
                error.assert_not_called()
            assert page.result is not None
            assert page.result.rms_residual_pct < 1.0
            with patch("kramers_kronig_gui.filedialog.asksaveasfilename", return_value=str(target)):
                page.export_results()
            with target.open(newline="", encoding="utf-8") as stream:
                rows = list(csv.reader(stream))
            assert len(rows) == len(frequency) + 1
            assert len(rows[0]) == 9
            exported = np.asarray(rows[1:], dtype=float)
            np.testing.assert_allclose(exported[:, 0], page.result.frequency)
            np.testing.assert_allclose(exported[:, 4], page.result.fitted.real)
            app.update_idletasks()
            page.on_return()
            assert app.active_page is None and app.home_page is not None
            app.update_idletasks()
            assert not errors, errors
        print("PASS: K-K home navigation, import, RC fit, plots, CSV export, and Return")
    finally:
        app.destroy()


if __name__ == "__main__":
    main()
