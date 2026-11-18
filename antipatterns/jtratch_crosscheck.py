#!/usr/bin/env python3
"""Milestone 4 (validation V1): compare our detector with JTratch, the authors' tool.

Usage: jtratch_crosscheck.py JT_DIR OUT_DIR
  JT_DIR  has one folder per library (lang, codec, compress, gson) holding the *_CatchBlock.csv that
          JTratch wrote (see run_jtratch.md for how it was built and run)
  OUT_DIR has blocks.csv and files.csv from detect.py; jtratch_crosscheck.txt and jtratch_blocks.csv are written there

JTratch gives one row per catch block with metrics (Logged, Abort, Default, EmptyBlock, NumThrown, ExceptionType, ...)
but no anti-pattern columns, so we turn the metrics into the same four flags:
  generic      : caught type is java.lang.Exception or java.lang.Throwable
  dummy        : empty body, or only logs/prints (Logged, MultiLog or Default) and does not throw
  log_and_throw: logs and throws
  interrupted  : caught type InterruptedException and the body does not throw
Blocks are matched on (library, file, line of the catch clause).
"""
import glob
import sys

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

ROOT = {"lang": ("Lang", "full/lang/"), "codec": ("Codec", "full/codec/"),
        "compress": ("Compress", "compress_utf8/"), "gson": ("Gson", "full/gson/")}
PATS = ["generic", "dummy", "log_and_throw", "interrupted"]
OURS = {"generic": "generic_catch", "dummy": "dummy_handler", "log_and_throw": "log_and_throw",
        "interrupted": "ignoring_interrupted"}


def kappa(a, b):
    a, b = np.asarray(a, bool), np.asarray(b, bool)
    po = (a == b).mean()
    pe = a.mean() * b.mean() + (1 - a.mean()) * (1 - b.mean())
    return float("nan") if pe == 1 else (po - pe) / (1 - pe)


def load_jtratch(jt_dir):
    frames = []
    for key, (lib, marker) in ROOT.items():
        path = glob.glob(f"{jt_dir}/{key}/*_CatchBlock.csv")[0]
        j = pd.read_csv(path)
        rel = j.FilePath.str.split(marker, n=1).str[1]
        if key != "compress":
            rel = rel.copy()
        else:
            rel = "src/main/java/" + rel
        j["library"], j["file"], j["line"] = lib, rel, j.StartLine
        thrown = j.NumThrown > 0
        logs = (j.Logged > 0) | (j.MultiLog > 0) | (j.Default > 0)
        j["generic"] = j.ExceptionType.isin(["java.lang.Exception", "java.lang.Throwable"]).astype(int)
        j["dummy"] = ((j.EmptyBlock > 0) | (logs & ~thrown)).astype(int)
        j["log_and_throw"] = (logs & thrown).astype(int)
        j["interrupted"] = (j.ExceptionType.str.endswith("InterruptedException") & ~thrown).astype(int)
        frames.append(j[["library", "file", "line", "ExceptionType"] + PATS])
    return pd.concat(frames, ignore_index=True)


def main(jt_dir, out):
    jt = load_jtratch(jt_dir)
    ours = pd.read_csv(f"{out}/blocks.csv")
    m = ours.merge(jt, on=["library", "file", "line"], how="outer", suffixes=("", "_jt"), indicator=True)
    lines = []
    say = lines.append
    say(f"our blocks {len(ours)}, JTratch blocks {len(jt)}, matched on library/file/line {int((m._merge == 'both').sum())}, "
        f"only ours {int((m._merge == 'left_only').sum())}, only JTratch {int((m._merge == 'right_only').sum())}")
    both = m[m._merge == "both"].copy()
    say("\nblock level, matched blocks (ours versus JTratch-derived flags):")
    say(f"{'pattern':14s} ours  jt  both  agree%  kappa")
    for p in PATS:
        a, b = both[OURS[p]].astype(bool), both[p + "_jt" if p + "_jt" in both else p].astype(bool)
        say(f"{p:14s} {int(a.sum()):4d} {int(b.sum()):3d} {int((a & b).sum()):4d}  {100 * (a == b).mean():5.1f}  {kappa(a, b):.2f}")
    dis = both[both[OURS["dummy"]].astype(bool) != both["dummy_jt" if "dummy_jt" in both else "dummy"].astype(bool)]
    say(f"\ndummy-handler disagreements: {len(dis)}")
    for r in dis.itertuples():
        say(f"  {r.library} {r.file.split('/')[-1]}:{r.line} ours={r.dummy_handler} jtratch={int(r.dummy)}  {str(r.snippet)[:70]!r}")
    both.to_csv(f"{out}/jtratch_blocks.csv", index=False)

    # file level: does the defective-versus-other finding survive with JTratch's flags?
    files = pd.read_csv(f"{out}/files.csv")
    files = files[files.catch_blocks > 0]
    jf = jt.groupby(["library", "file"])[PATS].max().reset_index()
    ff = files.merge(jf, on=["library", "file"], how="left", suffixes=("", "_jt")).fillna(0)
    say(f"\nfile level ({len(ff)} catch files):")
    for name, col in [("our Dummy Handler", "dummy_handler"), ("JTratch-derived dummy", "dummy")]:
        has = ff[col] > 0
        d = ff.defective == 1
        t = [[int((has & d).sum()), int((~has & d).sum())], [int((has & ~d).sum()), int((~has & ~d).sum())]]
        o, p = fisher_exact(t)
        say(f"  {name}: defective {t[0][0]}/{t[0][0] + t[0][1]}, other {t[1][0]}/{t[1][0] + t[1][1]}, "
            f"OR {o:.2f}, Fisher p {p:.3f}")
    a = ff.dummy_handler > 0
    b = ff.dummy > 0
    say(f"  file-level agreement on 'has a dummy handler': {100 * (a == b).mean():.1f}%, kappa {kappa(a, b):.2f}")
    open(f"{out}/jtratch_crosscheck.txt", "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: jtratch_crosscheck.py JT_DIR OUT_DIR")
    main(sys.argv[1], sys.argv[2])
