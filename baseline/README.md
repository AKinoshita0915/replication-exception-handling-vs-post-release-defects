# Baseline replication (RQ2)
Replicates de Padua and Shang, MSR 2018, on Hadoop 2.6 and Hibernate 5.0.

## To reproduce: 
install R 4.6.1 and RStudio, install the packages in sessionInfo.txt,
download the authors' package (guipadua.github.io/eh-model-defects2018),
replace analysis_functions.R with our version (one line changed, see baseline_change_log.md),
run 0-DataSourcesAnalysis.Rmd then 1-Model_Construction.Rmd.

### Adjustments
`analysis_functions.R` in this folder already contains our one-line fix, so nothing has to be changed by hand.
If you use the authors' original file instead, change line 270 in `modelSimplification` from
`if(class_refit != "try-error" && !is.na(refit)) {` to
`if(class_refit != "try-error" && !identical(refit, NA)) {`
(R 4.6 does not allow `&&` on a vector; see `baseline_change_log.md`, row 5). To check the change in an R session, run
`body(modelSimplification)` and look for the modified line.

## Results: 
- baseline_comparison.csv.
- Authors' saved output: *_BKP.csv.