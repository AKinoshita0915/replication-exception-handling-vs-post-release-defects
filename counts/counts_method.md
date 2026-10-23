# Library counts
Defect, following de Padua and Shang (MSR 2018, Sec. 3.3.1): a fixed defect in the issue tracker, reported after the release, connected to code changes by its ID.
Adaptation: JIRA is used for Apache libraries (issuetype = Bug, resolution = Fixed, created within one year after the release), while for Gson GitHub issues are taken (label = bug, closed, created in the window).
Fix commits: commits on the default branch, in the window, containing a defect key in their commit messages; the GitHub issue timeline was used as the secondary linking mechanism for Gson.
(a) = files with a catch clause at the release tag in distinct main source directories. (b) = files in (a) which were modified by the fix commits.
Constraints: one release per library; file renames are not considered; closed issues of Gson include ‘not planned’; the window may contain late fixes (see additional number with the window endpoint excluded); issue types are defined by labels in the trackers.