#!/usr/bin/env python3
"""Compare defective catch files with the other catch files, per anti-pattern.

Input : OUT_DIR/files.csv and blocks.csv written by detect.py
Output: OUT_DIR/prevalence_by_library.csv, OUT_DIR/comparison.csv (printed as well)
Only files with at least one parsed catch block are analysed (catch files whose only
'catch (' text sits in Javadoc examples are dropped).
"""
import sys

import pandas as pd
from scipy.stats import fisher_exact

PATS = ["generic_catch", "dummy_handler", "log_and_throw", "ignoring_interrupted"]
NAMES = {"generic_catch": "Generic Catch", "dummy_handler": "Dummy Handler",
         "log_and_throw": "Log and Throw", "ignoring_interrupted": "Ignoring Interrupted Exc."}


def main(out):
    files = pd.read_csv(f"{out}/files.csv")
    blocks = pd.read_csv(f"{out}/blocks.csv")
    files = files[files.catch_blocks > 0].copy()
    files["any_pattern"] = (files[PATS].sum(axis=1) > 0).astype(int)

    # 1. prevalence per library (files with at least one block of the pattern)
    rows = []
    for lib, g in list(files.groupby("library", sort=False)) + [("All four", files)]:
        row = {"library": lib, "catch_files": len(g), "defective": int(g.defective.sum())}
        for p in PATS + ["any_pattern"]:
            row[p] = int((g[p] > 0).sum())
        rows.append(row)
    prev = pd.DataFrame(rows)
    prev.to_csv(f"{out}/prevalence_by_library.csv", index=False)

    # 2. defective vs other catch files: Fisher exact on 'file has the pattern'
    comp = []
    for lib, g in [("All four", files), ("Lang+Compress", files[files.library.isin(["Lang", "Compress"])])]:
        for p in PATS + ["any_pattern"]:
            has = g[p] > 0
            d, n = g.defective == 1, g.defective == 0
            a, b = int((has & d).sum()), int((~has & d).sum())
            c, e = int((has & n).sum()), int((~has & n).sum())
            odds, pval = fisher_exact([[a, b], [c, e]])
            comp.append({"set": lib, "pattern": NAMES.get(p, "Any of the four"),
                         "defective_with": a, "defective_total": a + b,
                         "other_with": c, "other_total": c + e,
                         "pct_defective": round(100 * a / (a + b), 1) if a + b else None,
                         "pct_other": round(100 * c / (c + e), 1) if c + e else None,
                         "odds_ratio": None if odds in (float("inf"),) else round(odds, 2),
                         "p_fisher": round(pval, 3)})
    comp = pd.DataFrame(comp)
    comp.to_csv(f"{out}/comparison.csv", index=False)
    pd.set_option("display.width", 200)
    print(prev.to_string(index=False))
    print()
    print(comp.to_string(index=False))
    print("\nblocks per library:", blocks.groupby("library", sort=False).size().to_dict())


if __name__ == "__main__":
    main(sys.argv[1])
