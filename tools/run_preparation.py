"""Execute the pandas preparation notebook with the current Python interpreter."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def execute_preparation(run_dir, raw_path=None, project_root=ROOT, timeout=900):
    import nbformat
    from nbclient import NotebookClient
    from jupyter_client import KernelManager
    from jupyter_client.kernelspec import KernelSpecManager

    run_dir = Path(run_dir).resolve()
    project_root = Path(project_root).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    source = project_root / "notebooks" / "data_preparation.ipynb"
    notebook = nbformat.read(source, as_version=4)
    # Avoid mixing outputs from an earlier interactive run with this execution.
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None
    kernels = run_dir / "kernels"
    spec_dir = kernels / "preparation"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "kernel.json").write_text(json.dumps({
        "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
        "display_name": "Project preparation", "language": "python",
    }), encoding="utf-8")
    manager = KernelManager(
        kernel_name="preparation",
        kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernels)]),
    )
    client = NotebookClient(notebook, km=manager, timeout=timeout, allow_errors=False)
    environment = dict(os.environ, NFJ_PROJECT_ROOT=str(project_root), NFJ_AUTOMATED="1")
    environment["NFJ_RAW_PATH"] = str(Path(raw_path).resolve()) if raw_path else str(
        project_root / "data" / "raw" / "nofluff_it_jobs.csv"
    )
    try:
        client.execute(cwd=str(project_root), env=environment)
    finally:
        # Persist results even when a cell fails, without changing the source notebook.
        try:
            nbformat.write(notebook, run_dir / "data_preparation.executed.ipynb")
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    return run_dir / "data_preparation.executed.ipynb"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-path", type=Path)
    args = parser.parse_args()
    run_dir = ROOT / "artifacts" / "collection" / "preparation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    execute_preparation(run_dir, args.raw_path)
    print(f"Preparation complete: {run_dir}")


if __name__ == "__main__":
    main()
