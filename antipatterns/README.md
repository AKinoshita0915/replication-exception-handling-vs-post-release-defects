# Anti-pattern detector and comparison (Milestone 3)

Counts catch-block anti-patterns in the catch files of the four libraries and compares
defective catch files (changed by a post-release fix) with the other catch files.

## Inputs
- The four libraries checked out at the release commits in the report (Table II):
  commons-lang c8774fa74, commons-codec 2614a4ca, commons-compress 38dec7fb4, gson 828a97be.
- The file lists in `counts/` (`*_catch_files.txt`, `*_fixed_files.txt`, `*_fixed_files_nolimit.txt`).

## Run
```
pip install tree-sitter tree-sitter-java scipy pandas statsmodels openpyxl
python3 detect.py       SRC_DIR ../counts results     # catch blocks and per-file flags
python3 analyse.py      results                       # prevalence and Fisher tests
python3 stats_models.py SRC_DIR results               # size-controlled models
python3 make_sheet.py   SRC_DIR results               # manual-check sample (fixed seed)
python3 crosscheck.py   SRC_DIR ../counts results     # independent re-check + audit of unflagged blocks
python3 sensitivity.py  SRC_DIR results               # Milestone 4: robustness of the Dummy Handler result
python3 bsap_model.py   REPO_ROOT results            # Milestone 4: BASE vs BSAP, optimism-corrected R2 (needs lizard and full-history clones)
python3 jtratch_crosscheck.py results/jtratch results # Milestone 4: compare our flags with JTratch (how it was run: run_jtratch.md)
```
`SRC_DIR` holds the four checkouts in folders `commons-lang`, `commons-codec`,
`commons-compress` and `gson`. Re-running gives identical output.

## Detector rules (per `catch` clause, parsed with tree-sitter-java)
- **Generic Catch**: catches `Exception` or `Throwable`.
- **Dummy Handler**: empty body (comments only) or only logging or printing statements
  (`log.x()`, `logger.x()`, `System.out/err.print*()`, `printStackTrace()`). Note: in the ICPC 2017
  definitions an empty handler is a separate pattern (Catch and Do Nothing); we follow the
  Milestone 2 definition and count both together.
- **Log and Throw**: the body both logs and throws.
- **Ignoring Interrupted Exception**: catches `InterruptedException` and neither rethrows
  nor calls `interrupt()`.

## Limits
- Detection is syntactic. It does not follow exception flow, so it is not JTratch. Milestone 4 compared it with JTratch on all 325 blocks (`jtratch_crosscheck.py`, `run_jtratch.md`): Dummy Handler kappa 0.92, and all disagreements are cases where our flag follows the definition.
- These libraries hardly log, so Log and Throw never occurs and cannot be tested statistically, and
  almost every Dummy Handler (41 of 42 blocks) is an empty catch.
- The Dummy Handler definition does not cover handlers that only return a default value or
  continue/break (38 of the 254 unflagged blocks), so prevalence may be underestimated.

## Checks
- `results/manual_check_sheet_filled.xlsx`: manual check of 40 blocks. All 30 sampled flagged blocks are
  correct and none of the 10 sampled unflagged blocks is a miss. It uses the same definitions as the
  detector, so it checks the implementation, not the definitions.
- `crosscheck.py` re-implements the four flags without tree-sitter (`results/crosscheck.txt`): same 325
  blocks, no disagreement. It also classifies the 254 unflagged blocks by their body.

## Notes
- Lang has 41 catch files with a real catch block, not 49: eight listed files contain `catch (` only in
  Javadoc (see `results/files.csv`).

## Milestone 4: sensitivity analysis

`sensitivity.py` (needs statsmodels) writes `results/sensitivity.txt`: empty versus log-only Dummy Handler blocks (41 of 42 are empty), a bootstrap interval for the size-adjusted odds ratio (4.34, 95% 1.28 to 36.18), a permutation test within libraries (p 0.009), Mantel-Haenszel over libraries (OR 4.38, p 0.005 uncorrected, 0.013 with continuity correction) and over size bands (OR 3.51, p 0.026 / 0.056), leave-one-library-out (dropping Compress gives p 0.154, Lang 0.062) and the power of the pooled test (0.71 at the observed effect). The result keeps its direction in every check but is fragile; see the Milestone 4 report for the validation plan.

`bsap_model.py` (needs `lizard`, and full-history clones of the four releases in `REPO_ROOT/{lang,codec,compress,gson}`) compares a BASE model of size, complexity and process metrics (commits, churn and authors in the 12 months before the release) with BSAP (BASE plus Dummy Handler / Generic Catch) by optimism-corrected Nagelkerke R2 (1000 bootstrap resamples shared by BASE and BSAP), as in the original study. Complexity is dropped as redundant with size (rho 0.91). Results are in `results/bsap_model.txt` and `results/file_metrics.csv`: the apparent R2 rises by 0.04 to 0.06 when Dummy Handler is added; after the optimism correction the gain is +0.013 to +0.021 (other seeds: +0.004 to +0.032), similar to the 0.02 of the original study. Corrected R2 itself is negative for models with the library term, so only the BASE-to-BSAP change is informative. Pre-release defect counts are not used.
