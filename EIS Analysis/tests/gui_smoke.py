"""Manual GUI integration check; run with a desktop session available."""
from argparse import Namespace
from pathlib import Path
import sys
from unittest.mock import patch
import threading
from traceback import format_exc

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def main():
    import tempfile
    import eis_app
    with tempfile.TemporaryDirectory() as scratch:
        # Keep smoke-test configuration and recovery files out of the user's state.
        eis_app.user_directory = lambda kind: str(Path(scratch) / kind)
        import dearpygui.dearpygui as dpg
        from deareis.program import initialize_program
        from deareis.program.data_sets import select_data_set_files
        from deareis.program.project import save_project, save_project_as
        from deareis.signals import Signal
        import deareis.signals as signals
        from deareis.state import STATE
        errors = []
        completed = []
        signals.register(Signal.SHOW_ERROR_MESSAGE, lambda *a, **k: errors.append((a, k)))
        dpg.create_viewport(title=eis_app.APP_TITLE, width=1200, height=800, x_pos=30, y_pos=30)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        def stop_later():
            dpg.set_viewport_resize_callback(None)
            dpg.set_frame_callback(dpg.get_frame_count() + 60, dpg.stop_dearpygui)

        def capture_data():
            try:
                dpg.output_frame_buffer(str(ROOT / ".user-data" / "data-preview.png"))
                for _ in range(5):
                    dpg.split_frame()
                assert not errors, errors
                print("GUI OK: startup, sample imports, parameter edits, fitted-value reuse, save/cancel/overwrite/save-as, reopen, plots")
                completed.append(True)
            except BaseException as exc:
                errors.append(format_exc())
            finally:
                stop_later()

        def exercise():
            try:
                initialize_program(Namespace(data_files=[], project_files=[]))
                for _ in range(15):
                    dpg.split_frame()
                dpg.output_frame_buffer(str(ROOT / ".user-data" / "home-preview.png"))
                for _ in range(5):
                    dpg.split_frame()
                with patch("deareis.program.data_sets.choose_files", return_value=[]):
                    select_data_set_files()
                assert not STATE.projects
                sample = ROOT.parent / "Sample" / "Ni foil 2 cm2" / "Ni_foil_EIS 0.668 V.txt"
                with patch("deareis.program.data_sets.choose_files", return_value=[str(sample)]):
                    select_data_set_files()
                    select_data_set_files()
                project = STATE.get_active_project()
                assert len(STATE.projects) == 1
                assert len(project.get_data_sets()) == 2
                assert len({data.get_label() for data in project.get_data_sets()}) == 2
                tab = STATE.get_active_project_tab()
                assert dpg.get_value(tab.tab_bar) == tab.data_sets_tab.tab
                # Verify every raw EIS sample, retaining the duplicate-import checks above.
                samples = sorted(path for path in (ROOT.parent / "Sample").rglob("*EIS*.txt")
                                 if not path.name.startswith("CHI_sequence"))
                with patch("deareis.program.data_sets.choose_files", return_value=[str(p) for p in samples]):
                    select_data_set_files()
                assert len(project.get_data_sets()) == len(samples) + 2

                # Editable values must reach FitSettings without needing an initial fit.
                fitting = tab.fitting_tab
                menu = fitting.settings_menu
                menu.parse_cdc("R(RQ)(RQ)")
                table = menu.initial_parameters
                assert len(table.entries) == 7
                fields = table.entries[0][1]
                dpg.set_value(fields["value"], "2.5")
                dpg.set_value(fields["lower"], "1")
                dpg.set_value(fields["upper"], "5")
                dpg.set_value(fields["fixed"], True)
                import deareis
                settings = fitting.get_settings()
                resistor = deareis.parse_cdc(settings.cdc).get_elements()[0]
                assert resistor.get_value("R") == 2.5 and resistor.is_fixed("R")
                # Invalid draft values must neither alter the circuit nor start fitting.
                dpg.set_value(fields["value"], "9")
                try:
                    fitting.get_settings()
                    raise AssertionError("Invalid bounds were accepted")
                except ValueError:
                    pass
                assert table.circuit.get_elements()[0].get_value("R") == 2.5
                dpg.set_value(fields["value"], "2.5")
                table.apply()

                # Run a bounded fit on the measured sample and reuse its fitted values.
                from dataclasses import replace
                menu.parse_cdc("R{R=2}(R{R=10}Q{Y=0.001,n=0.9})")
                data = project.get_data_sets()[0]
                settings = replace(fitting.get_settings(), method=deareis.CNLSMethod.LEASTSQ,
                                   weight=deareis.Weight.MODULUS, max_nfev=300, timeout=30)
                fit = deareis.fit_circuit(data, settings, num_procs=1)
                project.add_fit(data, fit)
                tab.populate_fits(project, data)
                signals.emit(Signal.SELECT_FIT_RESULT, fit=fit, data=data)
                fitting.apply_fitted_values_as_initial_values()
                values = deareis.parse_cdc(fitting.get_settings().cdc).get_elements()[0].get_values()
                import numpy as np
                np.testing.assert_allclose(list(values.values()),
                                           list(fit.circuit.get_elements()[0].get_values().values()),
                                           rtol=1e-10, atol=1e-12)

                # Test the actual save handlers; native dialogs return controlled paths.
                with patch("deareis.program.project.choose_save_path", return_value=""):
                    save_project_as()
                assert not project.get_path()
                saved = Path(scratch) / "Practice project.json"
                with patch("deareis.program.project.choose_save_path", return_value=str(saved)):
                    save_project()
                assert saved.exists() and project.get_path() == str(saved)
                with patch("deareis.program.project.choose_save_path", side_effect=AssertionError("Save reopened dialog")):
                    save_project()
                count = len(STATE.projects)
                with patch("deareis.program.project.choose_save_path", return_value=str(saved)):
                    save_project_as()
                assert len(STATE.projects) == count
                reopened = deareis.Project.from_file(str(saved))
                assert len(reopened.get_data_sets()) == len(samples) + 2
                assert len(reopened.get_fits(reopened.get_data_sets()[0])) == 1
                # A failed Save As must not change the original identity or path.
                before_uuid = project.uuid
                with patch.object(project, "save", side_effect=OSError("Test write failure")):
                    try:
                        save_project(path=str(Path(scratch) / "failed.json"), replacement_uuid="0" * 32)
                        raise AssertionError("Expected write failure")
                    except OSError:
                        pass
                assert project.uuid == before_uuid and project.get_path() == str(saved)
                signals.emit(Signal.HIDE_BUSY_MESSAGE)
                copy_path = Path(scratch) / "Practice copy.json"
                original_uuid = project.uuid
                with patch("deareis.program.project.choose_save_path", return_value=str(copy_path)):
                    save_project_as()
                assert project.uuid == original_uuid and project.get_path() == str(saved)
                assert STATE.get_active_project().get_path() == str(copy_path)
                assert len(STATE.projects) == count + 1
                from eis_app.file_dialog import last_save_directory
                assert last_save_directory() == scratch
                # Capture the initial-value table before any fit on the new project tab.
                tab = STATE.get_active_project_tab()
                tab.select_fitting_tab()
                tab.fitting_tab.settings_menu.parse_cdc("R(RQ)(RQ)")
                # Allow queued tab-show and plot-axis callbacks to execute first.
                dpg.set_frame_callback(dpg.get_frame_count() + 60, capture_data)
            except BaseException as exc:
                errors.append(format_exc())
                stop_later()
        try:
            dpg.set_frame_callback(1, exercise)
            # Ensure a failed startup cannot leave a test window hanging indefinitely.
            timeout = threading.Timer(90, dpg.stop_dearpygui)
            timeout.start()
            dpg.start_dearpygui()
            timeout.cancel()
            assert not errors, errors
            assert completed, "GUI smoke test timed out"
        finally:
            dpg.destroy_context()


if __name__ == "__main__":
    (ROOT / ".user-data").mkdir(exist_ok=True)
    main()
