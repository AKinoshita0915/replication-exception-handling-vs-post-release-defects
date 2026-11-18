# Running JTratch for the Milestone 4 cross-check (V1)

JTratch (https://github.com/guipadua/JTratch, the tool of de Pádua and Shang) is published as source only. We built and ran it as follows.

1. **Java 8.** JTratch uses Eclipse JDT 3.11, which cannot read the Java 9+ runtime (it fails with a NullPointerException in `ASTUtilities.findKind`). Use a Java 8 JDK (`openjdk-8-jdk-headless`); it also provides the JAXB classes JTratch imports.
2. **Build** (no code changes):
   ```
   git clone https://github.com/guipadua/JTratch.git && cd JTratch
   mkdir bin && javac -nowarn -encoding UTF-8 -cp "lib/*" -d bin $(find src/main/java -name '*.java' | grep -v /sample/)
   ```
3. **Run** on the main-source folder of each release (full-history clones at the release commits, kept under `full/<lib>/`), one output folder per library; the Maven-repo argument can be an empty folder:
   ```
   mkdir out_lang && cd out_lang
   java -Dfile.encoding=ISO-8859-1 -Xmx3g -cp "../JTratch/bin:../JTratch/lib/*" ca.concordia.jtratch.JTratch ByFolder /abs/path/full/lang/src/main/java ../m2
   ```
   (Gson: `full/gson/gson/src/main/java`.) The `*_CatchBlock.csv` files are copied to `results/jtratch/<lib>/`.
4. **Compress needs one input fix.** `TarArchiveOutputStream.java` is not valid UTF-8, and JTratch reads sources as UTF-8 and crashes. We ran JTratch on a copy of `src/main/java` in which that one file was converted from ISO-8859-1 to UTF-8 (line numbers unchanged); the copy is called `compress_utf8/`.
5. Compare: `python3 jtratch_crosscheck.py results/jtratch results` writes `results/jtratch_crosscheck.txt` and `results/jtratch_blocks.csv`.

JTratch does not output anti-pattern columns, so `jtratch_crosscheck.py` derives the flags from its metrics (rules in the script header). This is our reading of JTratch's metrics, not the authors' own classification.

## Adjudicated disagreements (matched blocks: 325 of 325)

| Flag | Disagreements | Cause (checked by reading the code) | Who is right |
|---|---|---|---|
| Dummy Handler | 6 | The handler contains a nested `try` (retry with another encoding or fallback) whose own catch throws or returns. JTratch sees no throw at the top level of the handler and counts the block as logging-only. Examples: `TarArchiveEntry.java:1497, 2066`, `TarUtils.java:267, 490`, `LazilyParsedNumber.java:48`, `SerializationUtils.java:106`. | Ours: the handler does real work |
| Generic Catch | 7 | All are multi-catch (`A \| B`). JTratch reports the common supertype `java.lang.Exception`; the code never catches `Exception`. | Ours |
| Ignoring Interrupted | 1 | `BackgroundInitializer.java:343`, multi-catch containing `InterruptedException`, same reason | Ours |
