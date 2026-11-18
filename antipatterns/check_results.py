#!/usr/bin/env python3
"""Compare regenerated results with the numbers reported in Milestones 3 and 4.

Usage: check_results.py NEW_RESULTS_DIR [COMMITTED_RESULTS_DIR]
Exit status 0 if every check passes (checks that need the JTratch step are skipped if it was not run).
The deterministic files (blocks.csv, files.csv) must be identical to the committed ones.
"""
import filecmp
import os
import re
import sys

import pandas as pd

new = sys.argv[1]
old = sys.argv[2] if len(sys.argv) > 2 else None
checks = []  # (name, ok, detail)


def add(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def near(name, actual, expected, tol):
    add(name, abs(actual - expected) <= tol, f"got {actual}, expected {expected} +/- {tol}")


files = pd.read_csv(f"{new}/files.csv")
files = files[files.catch_blocks > 0]
blocks = pd.read_csv(f"{new}/blocks.csv")
d = files.defective == 1
add("catch blocks = 325", len(blocks) == 325, len(blocks))
add("catch files = 134, defective = 19", len(files) == 134 and int(d.sum()) == 19, f"{len(files)}, {int(d.sum())}")
dh = files.dummy_handler > 0
add("Dummy Handler files: 8 of 19 defective, 17 of 115 other",
    int((dh & d).sum()) == 8 and int((dh & ~d).sum()) == 17, f"{int((dh & d).sum())}, {int((dh & ~d).sum())}")
gc = files.generic_catch > 0
add("Generic Catch files: 2 of 19 defective, 17 of 115 other",
    int((gc & d).sum()) == 2 and int((gc & ~d).sum()) == 17)

txt = lambda f: open(f"{new}/{f}").read() if os.path.exists(f"{new}/{f}") else ""
m = re.search(r"Mantel-Haenszel across libraries: OR = ([\d.]+)", txt("models.txt"))
near("Mantel-Haenszel across libraries, OR", float(m.group(1)) if m else -1, 4.38, 0.02)
m = re.search(r"Nagelkerke R2 = ([\d.]+).*?\n.*?Nagelkerke R2 = ([\d.]+)", txt("models.txt"), re.S)
add("Nagelkerke R2 0.247 -> 0.307", bool(m) and abs(float(m.group(1)) - 0.247) < 0.001 and abs(float(m.group(2)) - 0.307) < 0.001)
s = txt("sensitivity.txt")
m = re.search(r"Adjusted OR .*? = ([\d.]+); bootstrap 95% percentile CI ([\d.]+) to ([\d.]+)", s)
if m:
    near("adjusted OR (log10 LOC + library)", float(m.group(1)), 4.34, 0.02)
    near("bootstrap CI lower", float(m.group(2)), 1.28, 0.15)
    near("bootstrap CI upper", float(m.group(3)), 36.2, 6.0)
else:
    add("sensitivity.txt parsed", False)
m = re.search(r"one-sided p = ([\d.]+)", s)
near("stratified permutation p", float(m.group(1)) if m else -1, 0.009, 0.003)
m = re.search(r"without Compress: .*?p ([\d.]+)", s)
near("leave out Compress, p", float(m.group(1)) if m else -1, 0.154, 0.002)
b = txt("bsap_model.txt")
gains = [float(x) for x in re.findall(r"same resamples: ([+-][\d.]+)", b)]
add("BSAP corrected R2 gain positive and small in all four variants",
    len(gains) == 4 and all(0.0 < g < 0.05 for g in gains), str(gains))
j = txt("jtratch_crosscheck.txt")
if j:
    m = re.search(r"matched on library/file/line (\d+)", j)
    add("JTratch: all 325 blocks matched", bool(m) and int(m.group(1)) == 325)
    m = re.search(r"^dummy\s+\d+\s+\d+\s+\d+\s+[\d.]+\s+([\d.]+)", j, re.M)
    near("JTratch Dummy Handler kappa", float(m.group(1)) if m else -1, 0.92, 0.01)
else:
    print("note: JTratch results not found, JTratch checks skipped")
if old:
    for f in ["blocks.csv", "files.csv"]:
        add(f"{f} identical to the committed file", filecmp.cmp(f"{new}/{f}", f"{old}/{f}", shallow=False))

bad = 0
for name, ok, detail in checks:
    print(("PASS  " if ok else "FAIL  ") + name + (f"  ({detail})" if detail != "" and not ok else ""))
    bad += not ok
print(f"\n{len(checks) - bad} of {len(checks)} checks passed")
sys.exit(1 if bad else 0)
