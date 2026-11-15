"""Record actual regression results for the fork-only Warp 2282 validation."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("baseline", "fixed"))
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path.cwd()
    sys.path.insert(0, str(root))
    import warp as wp

    if not Path(wp.__file__).resolve().is_relative_to(root / "warp"):
        raise RuntimeError(f"Expected checked-out Warp, imported {wp.__file__}")

    wp.config.load_module_max_workers = 0
    suite = unittest.defaultTestLoader.loadTestsFromName("warp.tests.tile.test_tile_padded")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    record = {
        "phase": args.phase,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "header_sha256": hashlib.sha256((root / "warp/native/tile.h").read_bytes()).hexdigest(),
        "warp_module": wp.__file__,
        "warp_version": wp.__version__,
        "tests_run": result.testsRun,
        "failures": [{"test": str(test), "traceback": detail} for test, detail in result.failures],
        "errors": [{"test": str(test), "traceback": detail} for test, detail in result.errors],
        "skipped": [{"test": str(test), "reason": reason} for test, reason in result.skipped],
    }
    Path(args.output).write_text(json.dumps(record, indent=2) + "\n")
    if args.phase == "baseline":
        return 0 if result.testsRun and result.failures and not result.errors and not result.skipped else 1
    return 0 if result.testsRun and result.wasSuccessful() and not result.skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
