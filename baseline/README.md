# Baseline replication (RQ2)
Replicates de Padua and Shang, MSR 2018, on Hadoop 2.6 and Hibernate 5.0.
To reproduce: install R 4.6.1 and RStudio, install the packages in sessionInfo.txt,
download the authors' package (guipadua.github.io/eh-model-defects2018),
replace analysis_functions.R with our version (one line changed, see baseline_change_log.md),
run 0-DataSourcesAnalysis.Rmd then 1-Model_Construction.Rmd.
Results: baseline_comparison.csv. Authors' saved output: *_BKP.csv.