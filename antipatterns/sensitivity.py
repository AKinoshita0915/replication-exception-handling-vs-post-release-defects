#!/usr/bin/env python3
"""Milestone 4 sensitivity checks on the Dummy Handler result (run after detect.py).

Usage: sensitivity.py SRC_DIR OUT_DIR
Writes OUT_DIR/sensitivity.txt. Checks whether the Dummy Handler association survives
(1) splitting empty from log-only handlers, (2) a bootstrap interval for the size-adjusted
odds ratio, (3) a permutation test stratified by library, (4) stratification by file size,
(5) leaving one library out, and reports the power of the pooled test.
"""
import re
import warnings
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import fisher_exact
from statsmodels.stats.contingency_tables import StratifiedTable
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

ROOT = {"Lang": "commons-lang", "Codec": "commons-codec", "Compress": "commons-compress", "Gson": "gson"}
warnings.filterwarnings("ignore")
rng = np.random.default_rng(5570)


def body_is_empty(snippet):
    m = re.search(r"\{(.*)\}\s*$", str(snippet), re.S)
    inner = m.group(1) if m else ""
    inner = re.sub(r"//.*|/\*.*?\*/", "", inner, flags=re.S)
    return inner.strip() == ""


def adj_or(df):
    X = pd.get_dummies(df[["logloc", "library"]], columns=["library"], drop_first=True).astype(float)
    X["dummy"] = df["dummy"].astype(float)
    X = sm.add_constant(X)
    try:
        r = sm.Logit(df["defective"].astype(float), X).fit(disp=0, maxiter=200)
        return float(np.exp(r.params["dummy"]))
    except Exception:
        return np.nan


def main(src, out):
    f = pd.read_csv(f"{out}/files.csv")
    b = pd.read_csv(f"{out}/blocks.csv")
    f = f[f.catch_blocks > 0].copy()
    f["loc"] = [sum(1 for _ in open(f"{src}/{ROOT[r.library]}/{r.file}", encoding="utf8", errors="replace"))
                for r in f.itertuples()]
    f["logloc"] = np.log10(f["loc"])
    f["dummy"] = (f.dummy_handler > 0).astype(int)
    lines = []
    say = lines.append

    # 1. empty versus log-only Dummy Handler blocks
    d = b[b.dummy_handler == 1].copy()
    d["is_empty"] = d.snippet.map(body_is_empty)
    say(f"Dummy Handler blocks: {len(d)}  empty: {int(d.is_empty.sum())}  log-only: {int((~d.is_empty).sum())}")
    key = d.groupby(["library", "file"]).is_empty.agg(["any", "all"]).reset_index()
    f = f.merge(key.rename(columns={"any": "has_empty"})[["library", "file", "has_empty"]], how="left",
                on=["library", "file"])
    f["has_empty"] = f.has_empty.fillna(False).astype(bool)
    f["has_logonly"] = f.merge(
        d[~d.is_empty].groupby(["library", "file"]).size().rename("n").reset_index(),
        how="left", on=["library", "file"]).n.fillna(0).values > 0
    for name in ["has_empty", "has_logonly"]:
        a = int((f[name] & (f.defective == 1)).sum()); bb = int((~f[name] & (f.defective == 1)).sum())
        c = int((f[name] & (f.defective == 0)).sum()); e = int((~f[name] & (f.defective == 0)).sum())
        o, p = fisher_exact([[a, bb], [c, e]])
        say(f"  {name}: defective {a}/{a+bb}, other {c}/{c+e}, OR {o:.2f}, Fisher p {p:.3f}")

    # 2. bootstrap interval for the size- and library-adjusted odds ratio
    est = adj_or(f)
    boots = []
    for _ in range(2000):
        s = f.sample(len(f), replace=True, random_state=int(rng.integers(1e9)))
        if s.defective.nunique() < 2 or s.dummy.nunique() < 2 or s.library.nunique() < 4:
            continue
        v = adj_or(s)
        if np.isfinite(v) and v < 1e3:
            boots.append(v)
    lo, hi = np.percentile(boots, [2.5, 97.5])
    say(f"\nAdjusted OR (log10 LOC + library) = {est:.2f}; bootstrap 95% percentile CI "
        f"{lo:.2f} to {hi:.2f} ({len(boots)} usable resamples)")
    say(f"  share of resamples with OR > 1: {np.mean(np.array(boots) > 1):.3f}")

    # 3. permutation test stratified by library (statistic: defective files with a Dummy Handler)
    obs = int(((f.dummy == 1) & (f.defective == 1)).sum())
    groups = [g for _, g in f.groupby("library")]
    cnt = 0
    N = 20000
    for _ in range(N):
        tot = 0
        for g in groups:
            tot += int(g.dummy.values[rng.permutation(len(g))][g.defective.values == 1].sum())
        cnt += tot >= obs
    say(f"\nStratified permutation test: observed {obs} defective files with a Dummy Handler, "
        f"one-sided p = {(cnt + 1) / (N + 1):.4f} ({N} permutations)")

    # 4. stratify by file size (tertiles of lines of code) and by library
    f["size_band"] = pd.qcut(f["loc"], 3, labels=False, duplicates="drop")
    tabs = []
    for band, g in f.groupby("size_band"):
        t = np.array([[((g.dummy == 1) & (g.defective == 1)).sum(), ((g.dummy == 0) & (g.defective == 1)).sum()],
                      [((g.dummy == 1) & (g.defective == 0)).sum(), ((g.dummy == 0) & (g.defective == 0)).sum()]])
        tabs.append(t)
        say(f"  size band {band} (n={len(g)}, {int(g.defective.sum())} defective): {t.tolist()}")
    st = StratifiedTable(tabs)
    r = st.test_null_odds(correction=True)
    lo2, hi2 = st.oddsratio_pooled_confint()
    say(f"Mantel-Haenszel over size bands: OR {st.oddsratio_pooled:.2f} "
        f"(95% CI {lo2:.2f} to {hi2:.2f}), p {st.test_null_odds(correction=False).pvalue:.3f} "
        f"uncorrected, {r.pvalue:.3f} with continuity correction")


    # 4b. interval estimates for the unadjusted pooled and library-stratified odds ratios
    from scipy.stats.contingency import odds_ratio as _or
    t_all = [[int(((f.dummy == 1) & (f.defective == 1)).sum()), int(((f.dummy == 0) & (f.defective == 1)).sum())],
             [int(((f.dummy == 1) & (f.defective == 0)).sum()), int(((f.dummy == 0) & (f.defective == 0)).sum())]]
    ci = _or(t_all).confidence_interval(0.95)
    say(f"\nPooled unadjusted OR {_or(t_all).statistic:.2f}, exact 95% CI {ci.low:.2f} to {ci.high:.2f}")
    lib_tabs = []
    for lib, g in f.groupby("library"):
        lib_tabs.append(np.array([[((g.dummy == 1) & (g.defective == 1)).sum(), ((g.dummy == 0) & (g.defective == 1)).sum()],
                                  [((g.dummy == 1) & (g.defective == 0)).sum(), ((g.dummy == 0) & (g.defective == 0)).sum()]]) + 0)
    stl = StratifiedTable([t for t in lib_tabs if t.sum(axis=1).min() > 0 and t.sum(axis=0).min() > 0])
    l1, h1 = stl.oddsratio_pooled_confint()
    say(f"Mantel-Haenszel by library (libraries with data in every margin): OR {stl.oddsratio_pooled:.2f}, "
        f"95% CI {l1:.2f} to {h1:.2f}, p {stl.test_null_odds(correction=False).pvalue:.3f} uncorrected, "
        f"{stl.test_null_odds(correction=True).pvalue:.3f} with continuity correction")

    # 5. leave one library out
    say("\nLeave one library out (Fisher on the remaining files):")
    for lib in ROOT:
        g = f[f.library != lib]
        t = [[int(((g.dummy == 1) & (g.defective == 1)).sum()), int(((g.dummy == 0) & (g.defective == 1)).sum())],
             [int(((g.dummy == 1) & (g.defective == 0)).sum()), int(((g.dummy == 0) & (g.defective == 0)).sum())]]
        o, p = fisher_exact(t)
        say(f"  without {lib}: n={len(g)}, table {t}, OR {o:.2f}, p {p:.3f}")

    # 6. power of the pooled comparison (Cohen's h on the observed shares) and sample needed
    p1, p0 = 8 / 19, 17 / 115
    h = proportion_effectsize(p1, p0)
    pw = NormalIndPower().power(h, nobs1=19, ratio=115 / 19, alpha=0.05)
    n80 = NormalIndPower().solve_power(h, power=0.8, ratio=115 / 19, alpha=0.05)
    n_half = NormalIndPower().solve_power(proportion_effectsize((p1 + p0) / 2 + 0.0, p0), power=0.8, ratio=115 / 19, alpha=0.05)
    say(f"\nPower at the observed shares (42.1% vs 14.8%), n=19 vs 115, alpha 0.05: {pw:.2f}")
    say(f"Defective files needed for 80% power at that effect (ratio 1:6): {n80:.0f}")
    say(f"If the true effect is half as large (shares {(p1 + p0) / 2:.3f} vs {p0:.3f}): {n_half:.0f} defective files")

    open(f"{out}/sensitivity.txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: sensitivity.py SRC_DIR OUT_DIR")
    main(sys.argv[1], sys.argv[2])
