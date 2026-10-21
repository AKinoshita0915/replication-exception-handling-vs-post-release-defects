**Working baseline.** To answer research question 2, we ran the authors' replication package (consisting of R notebooks and input data files) without modification against Hadoop 2.6 and Hibernate 5.0: does BSAP metrics outperform the BASE model of size, complexity, and change metrics? We provide the optimism-corrected Nagelkerke R2 of the catch-block model simplification (Table 1). Our results round to those in the paper: Hadoop 0.33 (BASE) and 0.35 (BSAP), Hibernate 0.21 and 0.23, with maximum difference of 0.004 from the author's own run saved. The same set of anti-patterns is statistically significant in the same direction: for Hadoop, Ignoring Interrupted Exception, Log and Throw, and Potentially Recoverable (all positive), for Hibernate, Catch SLOC and Dummy Handler (both positive). Therefore, RQ2 was successfully replicated. Small discrepancies are inevitable due to the lack of a fixed random seed in the bootstrap validation process. Replication required only one fix to R 4.6 (analysis_functions.R file) and a Pandoc-enabled RStudio. One of the differences we could not reconcile was that the third model of the package (BSFC, which is not needed for RQ2) has fewer predictors than that in the paper (23 and 19 compared to 31 and 27), hence its R^2 is lower than that of the paper (0.351 and 0.235 compared to 0.37 and 0.28).

## Table 1
Optimism-corrected Nagelkerke R^2 of the simplified catch-block models (RQ2). "Authors" is the saved output shipped in the replication package.

| Project | Model | Paper | Authors | Ours | Same significant anti-patterns and direction? |
|---|---|---|---|---|---|
| Hadoop | BASE | 0.33 | 0.329 | 0.329 | n/a |
| Hadoop | BSAP | 0.35 | 0.352 | 0.348 | Yes: Ignoring Interrupted Exception (+), Log and Throw (+), Potentially Recoverable (+) |
| Hibernate | BASE | 0.21 | 0.213 | 0.213 | n/a |
| Hibernate | BSAP | 0.23 | 0.235 | 0.232 | Yes: Catch SLOC (+), Dummy Handler (+) |

Note: differences of 0.001 to 0.004 are expected because the bootstrap has no fixed random seed. The package's third model (BSFC) is not part of RQ2 and uses fewer predictors than the paper (Hadoop 23 vs 31, Hibernate 19 vs 27): paper 0.37 and 0.28, package 0.351 and 0.235 (authors' saved run 0.350 and 0.231).