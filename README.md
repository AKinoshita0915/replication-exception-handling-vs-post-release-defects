# Exception-handling anti-patterns and post-release defects in small Java libraries

This is Group 3's project for ENGR5570G (Software Maintenance and Evolution) at Ontario Tech University.

We are repeating part of a published study: G. B. de Pádua and W. Shang, "Studying the relationship between exception handling practices and post-release defects", MSR 2018 ([doi](https://doi.org/10.1145/3196398.3196435), [authors' replication package](https://guipadua.github.io/eh-model-defects2018/)).

We only repeat RQ2 and only for Java. The question is whether exception-handling anti-patterns help explain post-release defects once the usual metrics (size, complexity, process) are already in the model. The paper calls the model with the usual metrics BASE and the one with the anti-pattern metrics added BSAP.

The paper used large projects. We wanted to see what happens on small ones, so we picked four libraries: Apache Commons Lang, Codec, Compress and Google Gson, one release of each.

## What is in the repository

- `baseline/` has our rerun of the original RQ2 on Hadoop 2.6 and Hibernate 5.0, using the authors' R scripts and data. It also has the change log and `sessionInfo.txt`. See `baseline/README.md`.
- `counts/` has the counts for the four libraries: file lists, bug keys, the counts table, a short note on how we counted, and the release tags and commits. See `counts/README.md`.
- `antipatterns/` has our anti-pattern detector, the analysis scripts, the results, and the manual-check sheet. See `antipatterns/README.md`.
- `reproduce.sh` and `requirements.txt` rebuild all the numbers for the four libraries (see below).

## How to rerun it

```
git clone https://github.com/AKinoshita0915/replication-exception-handling-vs-post-release-defects.git
cd replication-exception-handling-vs-post-release-defects
./reproduce.sh
```

You need Python 3.11 or newer, git and an internet connection. For the JTratch comparison you also need a Java 8 JDK. If the script can't find one it skips that step and says so. How we built and ran JTratch is in `antipatterns/run_jtratch.md`.

The script sets up a virtual environment, clones the four libraries and checks that each one is at the release commit we used, then runs the detector, the statistics, the sensitivity checks, the BASE vs BSAP comparison and the JTratch comparison. The last thing it does is run `antipatterns/check_results.py`, which compares the new numbers with the ones in our reports. If everything matches you see `16 of 16 checks passed`. On a clean folder it took under 3 minutes, plus the time to clone.

The Hadoop and Hibernate baseline is done separately in R. Its instructions are in `baseline/README.md`.

## Results so far

### Baseline: original RQ2 (optimism-corrected Nagelkerke R²)

| Project | BASE, paper / ours | BSAP, paper / ours |
|---|---|---|
| Hadoop 2.6 | 0.33 / 0.329 | 0.35 / 0.348 |
| Hibernate 5.0 | 0.21 / 0.213 | 0.23 / 0.232 |

The same anti-patterns come out significant with positive coefficients, and the Wald χ² values match the paper to two decimals. The R scripts don't fix a random seed, so small differences between runs are normal. We changed one line in `analysis_functions.R` (see `baseline/baseline_change_log.md`).

### Library counts (one release each, one-year window after the release)

| Library | Release | Main files | Files with catch blocks | Catch files changed by a bug fix |
|---|---|---|---|---|
| Commons Lang | 3.14.0 | 246 | 49 (41 with a real catch block) | 4 |
| Commons Codec | 1.16.0 | 80 | 12 | 1 |
| Commons Compress | 1.25.0 | 399 | 57 | 11 |
| Gson | 2.11.0 | 83 | 24 | 3 |

That gives 134 files with catch blocks, 325 catch blocks, and 19 files that had a bug fix in the year after the release.

### Anti-patterns in the four libraries

| Pattern | Defective catch files (19) | Other catch files (115) | Odds ratio | p |
|---|---|---|---|---|
| Generic Catch | 2 (10.5%) | 17 (14.8%) | 0.68 | 1.00 |
| Dummy Handler (empty or log-only) | 8 (42.1%) | 17 (14.8%) | 4.19 | 0.009 (0.037 with Bonferroni) |
| Log and Throw | 0 | 0 | n/a | n/a |
| Ignoring Interrupted Exception | 0 | 2 (1.7%) | n/a | 1.00 |

Only Dummy Handler stands out. With log10(lines of code) and library as the BASE model, adding it raises the Nagelkerke R² from 0.247 to 0.307 (likelihood-ratio p = 0.021).

### Milestone 4 checks

We tried to break the Dummy Handler result in several ways. It keeps its direction every time, but it is fragile with only 19 defective files:

- Adjusting for file size and library gives an odds ratio of 4.34 (bootstrap 95% interval 1.28 to 36.18). A permutation test inside each library gives p = 0.009.
- Leaving out one library at a time, the result stays significant without Codec (p = 0.011) and without Gson (p = 0.002), but not without Lang (p = 0.062) or without Compress (p = 0.154).
- Power at the observed effect is about 0.71. We would need around 24 defective files for 80%, and far more if the real effect is smaller.
- In a BASE vs BSAP comparison with size, process metrics and library, adding Dummy Handler improves the corrected R² only a little (about +0.013 to +0.021).
- We built the authors' tool JTratch from its public source and ran it on the same code. It finds the same 325 catch blocks. Its Dummy Handler flags agree with ours (κ 0.92), and the result is the same using its flags (9 of 19 vs 19 of 115, odds ratio 4.55, p = 0.005).

The details and the limits are in `antipatterns/README.md`.

## How the counts were made

1. Check out the release tag and keep the main-source Java files.
2. Keep the files with a catch block: `grep -rlE 'catch[[:space:]]*\(' src/main/java`.
3. Ask the issue tracker for bugs fixed in the window. For Apache JIRA that looks like `project = LANG AND issuetype = Bug AND resolution = Fixed AND created >= "2023-11-18" AND created <= "2024-11-18"` (the project key and dates change per library). Gson uses GitHub issues labelled `bug`.
4. List the commits in the window whose message names one of those issue keys, take the main-source files they changed, and count how many are in the list from step 2.

Files are matched by path, without rename tracking. The resulting file lists are in `counts/`.

## What is left

The baseline, the detector, the four-library comparison and the JTratch check are done. Still to do for the final report: more releases per library (to get more defective files), the return-only and continue/break handlers, a bigger manual check, and a clean final run of `reproduce.sh`.
