#!/usr/bin/env python3
"""Create a fake UE4/UE5 engine install so you can try uebuild without a
100 GB engine download. The fake RunUAT simulates a BuildPlugin run.

    python scripts/make_fake_engine.py demo/UE_5.3 --version 5.3.2
    python scripts/make_fake_engine.py demo/UE_4.27 --version 4.27.2

Simulate failure:

    UEBUILD_FAKE_UAT_FAIL=error uebuild build --plugin ... --engine 5.3
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uebuild.engine import EngineInstall  # noqa: E402
from uebuild.testing import create_fake_engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", help="where to create the fake engine")
    parser.add_argument("--version", default="5.3.2",
                        help="engine version, e.g. 5.3.2 or 4.27.2")
    args = parser.parse_args()
    root = create_fake_engine(args.root, version=args.version)
    install = EngineInstall.from_root(root)
    print("fake %s engine created at %s" % (install.family_label, install.version_str))
    print("  RunUAT: %s" % install.uat_script)
    print("register it with: uebuild engines add %s" % root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
