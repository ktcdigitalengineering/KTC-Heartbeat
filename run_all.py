import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

SCRIPTS = [
    # Must run first: issues (and reviews) read its admin lookup CSVs.
    "main_data_connector.py",
    "main_assets.py",
    "main_issues.py",
    "main_reviews.py",
    "main_rfi.py",
    "main_submittals.py",
]


def main():
    results = []

    for script in SCRIPTS:
        print(f"\n===== Running {script} =====", flush=True)
        started = time.time()

        completed = subprocess.run(
            [sys.executable, script],
            cwd=ROOT,
        )

        elapsed = time.time() - started
        results.append((script, completed.returncode, elapsed))
        print(
            f"===== {script} finished "
            f"(exit {completed.returncode}, {elapsed:.0f}s) =====",
            flush=True,
        )

    print("\n===== Summary =====")
    for script, returncode, elapsed in results:
        status = "OK" if returncode == 0 else f"FAILED (exit {returncode})"
        print(f"{script:<24} {status:<20} {elapsed:.0f}s")

    if any(returncode != 0 for _, returncode, _ in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
