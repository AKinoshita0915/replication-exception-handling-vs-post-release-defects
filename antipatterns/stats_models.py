#!/usr/bin/env python3
"""Size-controlled checks on the Dummy Handler result (run after detect.py).

Usage: stats_models.py SRC_DIR OUT_DIR
Writes OUT_DIR/models.txt. Compares a size-only model (log10 lines of code + library)
with the same model plus 'file has a Dummy Handler', mirroring BASE versus BSAP of the
original study but with far fewer metrics (the original used 39).
"""
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2, fisher_exact, mannwhitneyu
from statsmodels.stats.contingency_tables import StratifiedTable

ROOT = {"Lang": "commons-lang", "Codec": "commons-codec", "Compress": "commons-compress", "Gson": "gson"}


def main(src, out):
    f = pd.read_csv(f"{out}/files.csv")
    f = f[f.catch_blocks > 0].copy()
    f["loc"] = [sum(1 for _ in open(f"{src}/{ROOT[r.library]}/{r.file}", encoding="utf8", errors="replace"))
                for r in f.itertuples()]
    f["logloc"] = np.log10(f["loc"])
    f["dummy"] = (f.dummy_handler > 0).astype(int)
    n = len(f)
    lines = []
    say = lines.append

    d, o = f[f.defective == 1], f[f.defective == 0]
    say(f"catch files analysed: {n}  defective: {len(d)}")
    say(f"median lines of code: defective {d['loc'].median():.0f}, other {o['loc'].median():.0f} "
        f"(Mann-Whitney p={mannwhitneyu(d['loc'], o['loc']).pvalue:.4f})")
    say(f"median catch blocks per file: defective {d.catch_blocks.median():.0f}, other {o.catch_blocks.median():.0f}")

    def fit(cols):
        X = sm.add_constant(pd.get_dummies(f[cols + ["library"]], columns=["library"], drop_first=True).astype(float))
        return sm.Logit(f.defective, X).fit(disp=0)

    def nagelkerke(m):
        cs = 1 - np.exp(2 * (m.llnull - m.llf) / n)
        return cs / (1 - np.exp(2 * m.llnull / n))

    base, full = fit(["logloc"]), fit(["logloc", "dummy"])
    lr = 2 * (full.llf - base.llf)
    say(f"\nBASE (log10 LOC + library): Nagelkerke R2 = {nagelkerke(base):.3f}")
    say(f"BASE + Dummy Handler:        Nagelkerke R2 = {nagelkerke(full):.3f}  "
        f"(LR chi2 = {lr:.2f}, p = {chi2.sf(lr, 1):.3f})")
    say(f"Dummy Handler: odds ratio = {np.exp(full.params['dummy']):.2f}, p = {full.pvalues['dummy']:.3f}")
    say(f"predictors in the fuller model: 5; original budget (files/15) = {n / 15:.1f}; defective files = {len(d)}")

    tabs = []
    for lib, g in f.groupby("library"):
        t = [[((g.dummy == 1) & (g.defective == 1)).sum(), ((g.dummy == 0) & (g.defective == 1)).sum()],
             [((g.dummy == 1) & (g.defective == 0)).sum(), ((g.dummy == 0) & (g.defective == 0)).sum()]]
        say(f"{lib} 2x2 [[def&dummy, def&no], [other&dummy, other&no]] = {np.array(t).tolist()}")
        tabs.append(np.array(t))
    st = StratifiedTable(tabs)
    say(f"Mantel-Haenszel across libraries: OR = {st.oddsratio_pooled:.2f}, p = {st.test_null_odds().pvalue:.3f}")

    def tab(g):
        return [[((g.dummy == 1) & (g.defective == 1)).sum(), ((g.dummy == 0) & (g.defective == 1)).sum()],
                [((g.dummy == 1) & (g.defective == 0)).sum(), ((g.dummy == 0) & (g.defective == 0)).sum()]]

    say(f"\npooled Fisher p = {fisher_exact(tab(f))[1]:.4f}")
    worst, which = 0, ""
    for i, r in f[(f.defective == 1) & (f.dummy == 1)].iterrows():
        p = fisher_exact(tab(f.drop(i)))[1]
        if p > worst:
            worst, which = p, r.file.split("/")[-1]
    say(f"drop one defective Dummy-Handler file at a time: worst-case p = {worst:.3f} (dropping {which})")
    say("Bonferroni for the 4 patterns tested: p x 4 = %.3f" % min(1, 4 * fisher_exact(tab(f))[1]))
    text = "\n".join(lines)
    open(f"{out}/models.txt", "w").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main(*sys.argv[1:3])
