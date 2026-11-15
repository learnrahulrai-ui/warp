"""Record compiler regression results for fork-only Warp 2294 validation."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
import unittest


REGRESSIONS = (
    "warp.tests.test_codegen.TestCodeGen.test_returned_tile_storage_updates_forward_shared_memory",
    "warp.tests.test_codegen.TestCodeGen.test_returned_tile_storage_updates_nested_forward_shared_memory",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("baseline", "fixed", "codegen"))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path.cwd()
    sys.path.insert(0, str(root))
    import warp as wp

    if not Path(wp.__file__).resolve().is_relative_to(root / "warp"):
        raise RuntimeError(f"Expected checked-out Warp, imported {wp.__file__}")

    # These metadata regressions generate CUDA source without a CUDA launch.
    # The full module also runs its available CPU execution tests.
    wp.config.enable_cuda = False
    wp.config.load_module_max_workers = 0
    names = ("warp.tests.test_codegen",) if args.phase == "codegen" else REGRESSIONS
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = {
        "phase": args.phase,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_sha256": {
            name: hashlib.sha256((root / name).read_bytes()).hexdigest()
            for name in ("warp/_src/context.py", "warp/tests/test_codegen.py")
        },
        "warp_module": wp.__file__,
        "warp_version": wp.__version__,
        "python_version": sys.version,
        "platform": platform.platform(),
        "cuda_execution": False,
        "tests_run": result.testsRun,
        "failures": [{"test": str(test), "traceback": detail} for test, detail in result.failures],
        "errors": [{"test": str(test), "traceback": detail} for test, detail in result.errors],
        "skipped": [{"test": str(test), "reason": reason} for test, reason in result.skipped],
    }
    Path(args.output).write_text(json.dumps(record, indent=2) + "\n")
    if args.phase == "baseline":
        return (
            0
            if result.testsRun == len(REGRESSIONS)
            and len(result.failures) == len(REGRESSIONS)
            and not result.errors
            and not result.skipped
            else 1
        )
    if args.phase == "fixed":
        return 0 if result.testsRun == len(REGRESSIONS) and result.wasSuccessful() and not result.skipped else 1
    return 0 if result.testsRun and result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
