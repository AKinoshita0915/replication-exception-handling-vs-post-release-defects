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
- Detection is syntactic. It does not follow exception flow, so it is not JTratch.
- These libraries hardly log, so Log and Throw never occurs and cannot be tested, and
  almost every Dummy Handler is an empty catch.
- `results/manual_check_sheet_filled.xlsx` is the filled manual check (40 blocks):
  30 of 30 flagged blocks correct, 0 of 10 unflagged blocks missed. It uses the same definitions
  as the detector.
- `crosscheck.py` re-implements the four flags without tree-sitter (`results/crosscheck.txt`): same 325
  blocks, no disagreement. It also sorts the 254 unflagged blocks; 38 only return a default value or
  continue/break, which the Dummy Handler definition does not cover.
- Lang has 41 catch files with a real catch block, not 49: eight listed files contain `catch (`
  only in Javadoc (see `results/files.csv`).
