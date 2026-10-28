"""Integration checks: isolated notebook kernels; no network or production writes."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from run_preparation import execute_preparation


class PreparationExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "notebooks").mkdir()

    def notebook(self, source):
        import nbformat
        nbformat.write(nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(source)]),
                       self.root / "notebooks" / "data_preparation.ipynb")

    def test_current_python_working_directory_and_environment(self):
        self.notebook("import os, sys\nfrom pathlib import Path\n"
                      "assert str(Path.cwd()) == os.environ['NFJ_PROJECT_ROOT']\n"
                      "assert os.environ['NFJ_AUTOMATED'] == '1'\n"
                      f"assert sys.executable == {sys.executable!r}\n"
                      "print('EXECUTION_OK')")
        result = execute_preparation(self.root / "run", project_root=self.root)
        data = json.loads(result.read_text(encoding="utf-8"))
        self.assertEqual(data["cells"][0]["outputs"][0]["text"], ["EXECUTION_OK\n"])
        source = json.loads((self.root / "notebooks" / "data_preparation.ipynb").read_text())
        self.assertEqual(source["cells"][0]["outputs"], [])

    def test_failed_cell_is_saved_and_error_propagates(self):
        self.notebook("raise ValueError('intentional validation failure')")
        with self.assertRaises(Exception):
            execute_preparation(self.root / "failed", project_root=self.root)
        data = json.loads((self.root / "failed" / "data_preparation.executed.ipynb").read_text())
        self.assertEqual(data["cells"][0]["outputs"][0]["ename"], "ValueError")
