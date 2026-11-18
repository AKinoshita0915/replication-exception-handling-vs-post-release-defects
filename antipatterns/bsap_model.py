#!/usr/bin/env python3
"""Milestone 4: BASE versus BSAP on the four libraries, in the style of the original RQ2.

Usage: bsap_model.py REPO_ROOT OUT_DIR
  REPO_ROOT holds full-history clones checked out at the release: lang, codec, compress, gson
  OUT_DIR   holds files.csv written by detect.py; bsap_model.txt and file_metrics.csv are written there

BASE  = size, complexity and process metrics of each catch file (the original used 39 metrics;
        with 19 defective files we can only use a handful, after dropping redundant ones).
BSAP  = BASE + anti-pattern metrics (Generic Catch and Dummy Handler: files with at least one block).
Both models also contain the library. The score is the optimism-corrected Nagelkerke R^2
(bootstrap with 1000 resamples shared by BASE and BSAP, as in the original study). Process metrics are taken over the 12 months before the release.
Pre-release defect counts are not used (they would need a pre-release fix link we have not built).
"""
import re
import subprocess
import sys
import warnings

import lizard
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2, spearmanr

warnings.filterwarnings("ignore")
DIR = {"Lang": "lang", "Codec": "codec", "Compress": "compress", "Gson": "gson"}
rng = np.random.default_rng(5570)


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout


def process_metrics(repo):
    """commits, churn (added + deleted lines) and distinct authors per file, 12 months before the release."""
    date = git(repo, "log", "-1", "--format=%cI").strip()
    since = (pd.Timestamp(date) - pd.DateOffset(years=1)).isoformat()
    out = git(repo, "log", f"--since={since}", "--format=@@%H|%an", "--numstat", "--no-renames")
    rec = {}
    commit = author = None
    for line in out.splitlines():
        if line.startswith("@@"):
            commit, author = line[2:].split("|", 1)
        elif line.strip():
            a, d, path = line.split("\t", 2)
            if a == "-":
                continue
            r = rec.setdefault(path, {"commits": set(), "churn": 0, "authors": set()})
            r["commits"].add(commit); r["churn"] += int(a) + int(d); r["authors"].add(author)
    return rec


def nagelkerke(res, n):
    ll0 = sm.Logit(res.model.endog, np.ones((n, 1))).fit(disp=0).llf
    cs = 1 - np.exp((2 / n) * (ll0 - res.llf))
    return cs / (1 - np.exp((2 / n) * ll0))


def fit(y, X):
    return sm.Logit(y, sm.add_constant(X, has_constant="add")).fit(disp=0, maxiter=300, method="bfgs")


def r2_on(res, y, X):
    """Nagelkerke R^2 of fitted coefficients evaluated on (y, X)."""
    Xc = sm.add_constant(X, has_constant="add")
    p = np.clip(1 / (1 + np.exp(-(Xc @ res.params.values))), 1e-9, 1 - 1e-9)
    ll = float(np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
    n = len(y)
    pb = y.mean()
    ll0 = n * (pb * np.log(pb) + (1 - pb) * np.log(1 - pb))
    return (1 - np.exp((2 / n) * (ll0 - ll))) / (1 - np.exp((2 / n) * ll0))


def corrected_r2(y, X, idxs):
    """Optimism-corrected Nagelkerke R^2 (Efron bootstrap). idxs is a list of resample indices shared by all
    models of one comparison, so that BASE and BSAP are corrected on the same resamples (paired)."""
    res = fit(y, X)
    app = r2_on(res, y, X)
    opt = []
    for idx in idxs:
        yb, Xb = y.iloc[idx], X.iloc[idx]
        if yb.nunique() < 2:
            continue
        try:
            rb = fit(yb, Xb)
            opt.append(r2_on(rb, yb, Xb) - r2_on(rb, y, X))
        except Exception:
            continue
    return app, app - float(np.mean(opt)), len(opt)


def main(root, out):
    f = pd.read_csv(f"{out}/files.csv")
    f = f[f.catch_blocks > 0].copy()
    rows = []
    for lib, g in f.groupby("library", sort=False):
        repo = f"{root}/{DIR[lib]}"
        pm = process_metrics(repo)
        for r in g.itertuples():
            path = f"{repo}/{r.file}"
            src = open(path, encoding="utf8", errors="replace").read()
            info = lizard.analyze_file.analyze_source_code(r.file, src)
            m = pm.get(r.file, {"commits": set(), "churn": 0, "authors": set()})
            rows.append(dict(library=lib, file=r.file, defective=r.defective, loc=src.count("\n") + 1,
                             ccn=sum(fn.cyclomatic_complexity for fn in info.function_list),
                             commits=len(m["commits"]), churn=m["churn"], authors=len(m["authors"]),
                             generic=int(r.generic_catch > 0), dummy=int(r.dummy_handler > 0)))
    d = pd.DataFrame(rows)
    d.to_csv(f"{out}/file_metrics.csv", index=False)
    say_lines = []
    say = say_lines.append
    n, ev = len(d), int(d.defective.sum())
    say(f"files {n}, defective {ev}; paper's budget (files/15) = {n / 15:.1f} degrees of freedom; "
        f"events per degree of freedom is the real limit ({ev} defective files)")

    # BASE metrics on a log scale, then drop redundant ones (|Spearman| > 0.7, keep the first in this order)
    cand = {"logLOC": np.log10(d["loc"]), "logChurn": np.log10(1 + d.churn), "logCCN": np.log10(1 + d.ccn),
            "logCommits": np.log10(1 + d.commits), "logAuthors": np.log10(1 + d.authors)}
    X = pd.DataFrame(cand)
    keep = []
    for c in cand:
        if all(abs(spearmanr(X[c], X[k])[0]) <= 0.7 for k in keep):
            keep.append(c)
    say("BASE metrics kept after the redundancy check (|rho|<=0.7): " + ", ".join(keep))
    dropped = [c for c in cand if c not in keep]
    if dropped:
        say("  dropped as redundant: " + ", ".join(
            f"{c} (rho {max(abs(spearmanr(X[c], X[k])[0]) for k in keep):.2f})" for c in dropped))
    lib = pd.get_dummies(d.library, drop_first=True).astype(float)
    y = d.defective.astype(float)
    for label, XB in [("with library", pd.concat([X[keep], lib], axis=1)),
                      ("pooled, no library term", X[keep].copy()),
                      ("size only (log LOC) + library", pd.concat([X[["logLOC"]], lib], axis=1)),
                      ("size only (log LOC), pooled", X[["logLOC"]].copy())]:
        say(f"\n== BASE metrics: {label} ==")
        models = {"BASE": XB,
                  "BSAP (BASE + Dummy Handler)": XB.assign(dummy=d.dummy.astype(float)),
                  "BSAP (BASE + Dummy Handler + Generic Catch)": XB.assign(dummy=d.dummy.astype(float),
                                                                             generic=d.generic.astype(float))}
        say("model                                          df  apparent R2  optimism-corrected R2")
        fits = {}
        idxs = [rng.integers(0, len(y), len(y)) for _ in range(1000)]
        corr = {}
        for name, Xm in models.items():
            res = fit(y, Xm)
            app, cor, used = corrected_r2(y, Xm, idxs)
            corr[name] = cor
            fits[name] = res
            say(f"{name:46s} {Xm.shape[1]:2d}   {app:.3f}        {cor:.3f}   ({used} bootstrap fits)")
        base = fits["BASE"]
        say(f"corrected R2 gain of BSAP (Dummy Handler) over BASE, same resamples: "
            f"{corr['BSAP (BASE + Dummy Handler)'] - corr['BASE']:+.3f}")
        for name in list(models)[1:]:
            lr = 2 * (fits[name].llf - base.llf)
            dfd = models[name].shape[1] - XB.shape[1]
            say(f"LR test {name} vs BASE: chi2 = {lr:.2f}, df = {dfd}, p = {chi2.sf(lr, dfd):.3f}")
        full = fits["BSAP (BASE + Dummy Handler)"]
        for term in ["dummy"] + list(XB.columns):
            w = (full.params[term] / full.bse[term]) ** 2
            say(f"  Wald chi2 {term}: {w:.2f} (coef {full.params[term]:+.2f}, OR {np.exp(full.params[term]):.2f}, "
                f"p {chi2.sf(w, 1):.3f})")
    open(f"{out}/bsap_model.txt", "w").write("\n".join(say_lines) + "\n")
    print("\n".join(say_lines))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: bsap_model.py REPO_ROOT OUT_DIR")
    main(sys.argv[1], sys.argv[2])
