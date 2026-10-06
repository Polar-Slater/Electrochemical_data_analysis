import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from eis_app import file_dialog


class SaveDialogTests(unittest.TestCase):
    def test_remember_folder_and_ignore_missing_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("eis_app.user_directory", return_value=directory):
                file_dialog.remember_save_directory(Path(directory) / "sample.json")
                self.assertEqual(file_dialog.last_save_directory("fallback"), str(Path(directory).resolve()))
                (Path(directory) / "dialogs.json").write_text(json.dumps({"save_directory": str(Path(directory) / "missing")}))
                self.assertEqual(file_dialog.last_save_directory("fallback"), "fallback")

    def test_native_save_options_and_cancel(self):
        import io
        for result in ("", "D:/some folder/test.json"):
            with self.subTest(result=result), patch("tkinter.Tk") as root, \
                 patch("tkinter.filedialog.asksaveasfilename", return_value=result) as save, \
                 patch.object(sys, "argv", ["dialog", "D:/some folder", "save", "test.json"]), \
                 patch("sys.stdout", new_callable=io.StringIO) as output:
                file_dialog.show_dialog()
                self.assertEqual(json.loads(output.getvalue()), result)
                self.assertTrue(save.call_args.kwargs["confirmoverwrite"])
                self.assertEqual(save.call_args.kwargs["defaultextension"], ".json")
                self.assertEqual(save.call_args.kwargs["initialfile"], "test.json")
                root.return_value.destroy.assert_called_once()
