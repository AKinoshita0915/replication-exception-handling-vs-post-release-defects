# Library counts

 These are rough counts to judge whether small Java libraries have enough history for the replication study. They are not model results (those come in A3).

## What was done
For each candidate library we picked one release, took the year after it as the window, and counted:
- **(a)** main-source files that contain a catch block, at the release tag;
- **(b)** how many of those files were changed by a commit that fixes a defect reported in the window.

## How a defect was defined (following de Padua and Shang, MSR 2018, Section 3.3.1)
A fixed defect in the issue tracker, reported after the release, linked to code changes through its ID.
- **Lang, Codec, Compress:** JIRA issues with type Bug and resolution Fixed, created in the window. A commit is a fix if its message cites the issue key (for example LANG-1735).
- **Gson:** no JIRA. GitHub issues labelled bug, closed, created in the window. Commit messages mostly cite pull request numbers, so we also looked at the commit IDs in each issue's GitHub timeline.

## Results
| Library | Release (date) | Source files | (a) Catch files | Bugs in window | (b) Overlap | (b) if fixes after window count |
|---|---|---|---|---|---|---|
| Lang | 3.14.0 (2023-11-18) | 246 | 49 | 16 | 4 | 5 |
| Codec | 1.16.0 (2023-06-17) | 80 | 12 | 7 | 1 | 1 |
| Compress (backup) | 1.25.0 (2023-11-12) | 399 | 57 | 24 | 11 | 11 |
| Gson | 2.11.0 (2024-05-19) | 83 | 24 | 28 | 3 | 3 |

Full table with more columns: `counts_table.csv`. Method summary: `counts_method.md`.

## What the numbers show
- All four samples are small. The original study modelled 890 (Hadoop) and 440 (Hibernate) files with catch blocks. At one predictor per 15 files, one release of these libraries supports 0 to 3 predictors.
- Codec is too small to use on its own (12 files, 1 overlap).
- Compress has the most data (57 files, 11 overlap), then Lang (49, 4).
- Linking: Lang, Codec and Compress link well (sampled commits are real bug fixes, with a few test or Javadoc commits in Compress). In Lang, 6 of 16 bugs have no fix commit in the window (3 were fixed later, 3 cite no key); Compress has 4 of 24 and Codec 2 of 7 like this.
- Gson links poorly: only 2 of 28 bug issues are cited in commit messages and 5 of 28 appear in the issue timeline; 12 of the 28 were closed as "not planned"; several linked commits are build or dependency changes.

## Limits
One release per library (chosen so that a full year of history follows it, not by comparing several). File renames are ignored. The window can miss late fixes (see the "after window" column). The issue types and labels are those of the trackers and were not checked by hand beyond sampling commit messages.

## Files
- `*_catch_files.txt`: files with catch blocks at the release tag
- `*_bug_keys.txt` / `gson_bug_numbers.txt`: the defect IDs used
- `*_fixed_files.txt`: files changed by fix commits in the window; `*_fixed_files_nolimit.txt`: same with no window end
- `gson_link_commits.txt`, `gson_fixed_files_timeline.txt`: Gson links from the GitHub issue timeline

## To repeat for one library (example: Lang)
```
git clone https://github.com/apache/commons-lang.git && cd commons-lang
git log -1 --format=%cs rel/commons-lang-3.14.0          # release date
git checkout rel/commons-lang-3.14.0
find src/main/java -name "*.java" | wc -l                 # source files
grep -rlE 'catch[[:space:]]*\(' src/main/java --include='*.java' | sort > ../lang_catch_files.txt
# bug keys from JIRA (Bug, Fixed, created in window):
curl -s -G "https://issues.apache.org/jira/rest/api/2/search" \
  --data-urlencode 'jql=project = LANG AND issuetype = Bug AND resolution = Fixed AND created >= "2023-11-18" AND created <= "2024-11-18"' \
  --data-urlencode 'fields=key' --data-urlencode 'maxResults=1000' > ../lang_bugs.json
grep -o '"key":"LANG-[0-9]*"' ../lang_bugs.json | cut -d'"' -f4 | sort -u > ../lang_bug_keys.txt
git checkout master
PAT="($(paste -sd'|' ../lang_bug_keys.txt))([^0-9]|$)"
git log master --since=2023-11-18 --until=2024-11-18 --no-merges -E --grep="$PAT" --name-only --pretty=format: -- src/main/java | grep '\.java$' | sort -u > ../lang_fixed_files.txt
comm -12 ../lang_catch_files.txt ../lang_fixed_files.txt | wc -l    # (b)
```

## Release identifiers
| Library | Repository | Release tag | Commit | Release date |
|---|---|---|---|---|
| Lang | github.com/apache/commons-lang | rel/commons-lang-3.14.0 | c8774fa74 | 2023-11-18 |
| Codec | github.com/apache/commons-codec | rel/commons-codec-1.16.0 | 2614a4ca | 2023-06-17 |
| Compress | github.com/apache/commons-compress | rel/commons-compress-1.25.0 | 38dec7fb4 | 2023-11-12 |
| Gson | github.com/google/gson | gson-parent-2.11.0 | 828a97be | 2024-05-19 |

Check one: `git log -1 --format='%h %cs' rel/commons-lang-3.14.0` should print `c8774fa74 2023-11-18`.

Environment for these counts: macOS Tahoe 26.5.2 (Apple silicon), git, grep and curl only. JIRA queries and the GitHub issues API were run on 21 Oct 2026. Baseline environment: R 4.6.1 (see baseline/sessionInfo.txt). Java is not used yet (needed for JTratch).
