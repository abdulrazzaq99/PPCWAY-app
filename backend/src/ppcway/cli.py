"""`python -m ppcway.cli audit <site>`: run the eight checks from a terminal and print the report."""

from __future__ import annotations

import json
import sys

from ppcway.audit.runner import run_audit
from ppcway.config import load_settings


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "audit":
        print("usage: python -m ppcway.cli audit <site> [--json]")
        return 2
    report = run_audit(argv[1], load_settings())
    if "--json" in argv:
        print(json.dumps(report.as_dict(), indent=2))
        return 0
    took = (report.finished_at - report.started_at).total_seconds() if report.finished_at else 0
    print(f"{report.site}  {report.pages_read} pages  {took:.0f}s  {report.counts}")
    for f in report.findings:
        print(f"\n[{f.status:9}] {f.title}\n  {f.summary}")
        for d in f.detail:
            print(f"    - {d}")
        if f.fix:
            print(f"  Fix: {f.fix}")
    for n in report.notes:
        print(f"\nnote: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
