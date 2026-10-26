# Baseline replication (RQ2)
Replicates de Padua and Shang, MSR 2018, on Hadoop 2.6 and Hibernate 5.0.

## To reproduce: 
install R 4.6.1 and RStudio, install the packages in sessionInfo.txt,
download the authors' package (guipadua.github.io/eh-model-defects2018),
replace analysis_functions.R with our version (one line changed, see baseline_change_log.md),
run 0-DataSourcesAnalysis.Rmd then 1-Model_Construction.Rmd.

### Adjustments
In analysis_functions.R, there is known problem at modelSimplification method. Apply the following fix:
    In line 270 ( if(class_refit != "try-error" && !identical(refit, NA)) {... ), replace as: 
        if(!inherits(refit, "try-error") && !identical(refit, NA)) {...
    Save and run the file.

OR in console:
    fix(modelSimplification)
    New window would be pop-up. Find ( if(class_refit != "try-error" && !identical(refit, NA)) {... ), replace with:
        if(!inherits(refit, "try-error") && !identical(refit, NA)) {...
    Click "Save" to apply change.

veryfy the update in the session by 
body(modelSimplification), and find modified section.

## Results: 
- baseline_comparison.csv.
- Authors' saved output: *_BKP.csv.