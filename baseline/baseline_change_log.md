# Baseline change log
Replication package: de Padua and Shang, MSR 2018, "eh-model-defects2018_scripts_with_input_data" (scripts, input data and the authors' saved output).
Run date: Wed 21 Oct 2026. Scope: RQ2 only, BASE versus BASE + anti-patterns (BSAP), models CAT.BASE and CAT.BSAP, Hadoop and Hibernate.

## Environment
- macOS Tahoe 26.5.2, Apple silicon (aarch64-apple-darwin23)
- R 4.6.1 (2026-06-24), RStudio (bundles Pandoc)
- Packages: rms 8.1-1, Hmisc 5.3-0, plotly 4.12.1, e1071 1.7-17, caret 7.0-1, logistf 1.26.1, rmarkdown 2.32, knitr 1.52, ggplot2 4.0.3
- Full output of sessionInfo() is saved with the artifacts.

## Changes and problems, in order
| # | What happened | What we did | Effect on results |
|---|---|---|---|
| 1 | The CRAN mirror pop-up failed in R.app ("argument is of length zero") | Set the mirror in code: options(repos = c(CRAN = "https://cloud.r-project.org")) | None |
| 2 | Rendering in R.app failed: "pandoc version 2.8 or higher is required" | Ran the notebooks from RStudio, which bundles Pandoc | None |
| 3 | BiodiversityR installed but did not load in the session (the notebook only calls require() on it and never uses it) | Left as is; no code in the notebooks or helper scripts calls it | None observed |
| 4 | Notebook 0 (0-DataSourcesAnalysis.Rmd) must run first: it creates 0-all_no_missing.RData, which is not in the package | Ran notebook 0, then notebook 1 | None |
| 5 | Notebook 1 stopped in chunk "unnamed-chunk-16" (modelSimplification), analysis_functions.R line 270: `if(class_refit != "try-error" && !is.na(refit))`. R 4.6 does not allow `&&` on a vector longer than 1 (is.na of a fitted model returns many values). | Changed `!is.na(refit)` to `!identical(refit, NA)`. Same meaning: skip when the refit is NA. | None expected; results match the authors' run |

All default settings for analysis, thresholds, bootstrap iterations, and formulas were used. There is no seed value specified for the scripts, which means slight differences occur between runs.
