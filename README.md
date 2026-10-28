# Replicating exception-handling anti-patterns vs. post-release defects in small Java libraries

Group 3, ENGR5570G Software Maintenance and Evolution, Ontario Tech University.

This repository holds the artifacts for our partial replication of
G. B. de Pádua and W. Shang, "Studying the relationship between exception handling
practices and post-release defects", MSR 2018
(doi: [10.1145/3196398.3196435](https://doi.org/10.1145/3196398.3196435);
authors' replication package: https://guipadua.github.io/eh-model-defects2018/).

We replicate **RQ2 only, Java projects only**: do exception-handling anti-patterns
explain post-release defects beyond traditional metrics (a BASE model versus a BSAP
model that adds anti-pattern metrics)?

## What is in this repository

| Folder | Content |
|---|---|
| [`baseline/`](baseline/) | Reproduction of the original RQ2 on Hadoop 2.6 and Hibernate 5.0 with the authors' R scripts and data: our version of `analysis_functions.R`, rendered notebooks, result CSVs, the change log, and `sessionInfo.txt`. See [`baseline/README.md`](baseline/README.md). |
| [`counts/`](counts/) | Library counts for Apache Commons Lang, Codec, Compress and Google Gson: file lists, bug keys, `counts_table.csv`, the method note, and the release identifiers (tags and commits). See [`counts/README.md`](counts/README.md). |

## Results so far

**Baseline (original RQ2, optimism-corrected Nagelkerke R²)**

| Project | BASE (paper / ours) | BSAP (paper / ours) |
|---|---|---|
| Hadoop 2.6 | 0.33 / 0.329 | 0.35 / 0.348 |
| Hibernate 5.0 | 0.21 / 0.213 | 0.23 / 0.232 |

The same anti-patterns are significant, all with positive coefficients, and their Wald χ²
values match the paper to two decimals. The scripts use no fixed random seed, so small
differences between runs are expected. The only code change is one line in
`analysis_functions.R` (see `baseline/baseline_change_log.md`).

**Library counts (one release per library, one-year post-release window)**

| Library | Release | Main files | (a) files with catch blocks | (b) catch files changed by a fix |
|---|---|---|---|---|
| Commons Lang | 3.14.0 | 246 | 49 | 4 |
| Commons Codec | 1.16.0 | 80 | 12 | 1 |
| Commons Compress | 1.25.0 | 399 | 57 | 11 |
| Gson | 2.11.0 | 83 | 24 | 3 |

## How the counts were made

1. Check out the release tag and keep main-source Java files.
2. Keep files with a catch block: `grep -rlE 'catch[[:space:]]*\(' src/main/java`.
3. Query the tracker for bugs fixed in the window. Apache JIRA example:
   `project = LANG AND issuetype = Bug AND resolution = Fixed AND created >= "2023-11-18" AND created <= "2024-11-18"`
   (project key and dates change per library). Gson uses GitHub issues labelled `bug`.
4. List commits in the window whose message cites one of those issue keys, take the
   main-source files they changed, and count the overlap with step 2.

Files are matched by path without rename tracking. The resulting file lists are in `counts/`.

## Status

The baseline reproduction is complete. The anti-pattern detector (JTratch or a lightweight
alternative), open-source metrics and the model on the new libraries are still to do.
