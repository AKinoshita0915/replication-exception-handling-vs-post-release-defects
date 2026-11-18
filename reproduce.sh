#!/usr/bin/env bash
# Regenerates every number in the Milestone 3 and 4 reports from scratch.
#   ./reproduce.sh [WORKDIR]      (default WORKDIR: ./work, ignored by git)
# Needs: python3 (3.11+), git, internet access. For the JTratch cross-check also a Java 8 JDK
# (set JAVA8_HOME, or have `/usr/libexec/java_home -v 1.8` or /usr/lib/jvm/java-8-* available);
# without Java 8 that one step is skipped and reported.
# Time: about 15 minutes (most of it cloning the four libraries).
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
WORK="${1:-$REPO/work}"
mkdir -p "$WORK"; WORK="$(cd "$WORK" && pwd)"
AP="$REPO/antipatterns"
RES="$WORK/results"
mkdir -p "$RES"
say() { printf '\n== %s\n' "$*"; }

say "1/6 Python environment ($WORK/venv)"
[ -d "$WORK/venv" ] || python3 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q -r "$REPO/requirements.txt"
PY="$WORK/venv/bin/python3"

say "2/6 The four libraries at the release commits (full history; needed for process metrics)"
clone() {  # dir url tag expected-short-hash
  if [ ! -d "$WORK/full/$1/.git" ]; then
    git clone -q --single-branch --branch "$3" "$2" "$WORK/full/$1"
  fi
  got=$(git -C "$WORK/full/$1" log -1 --format=%h)
  case "$got" in "$4"*) echo "  $1 at $got (ok)";; *) echo "  $1 is at $got, expected $4"; exit 1;; esac
}
mkdir -p "$WORK/full" "$WORK/src"
clone lang     https://github.com/apache/commons-lang.git     rel/commons-lang-3.14.0     c8774fa
clone codec    https://github.com/apache/commons-codec.git    rel/commons-codec-1.16.0    2614a4c
clone compress https://github.com/apache/commons-compress.git rel/commons-compress-1.25.0 38dec7f
clone gson     https://github.com/google/gson.git             gson-parent-2.11.0          828a97b
for pair in lang:commons-lang codec:commons-codec compress:commons-compress gson:gson; do
  ln -sfn "$WORK/full/${pair%%:*}" "$WORK/src/${pair##*:}"
done

say "3/6 Detector, comparison, models, independent re-check (Milestone 3)"
cd "$AP"
$PY detect.py "$WORK/src" "$REPO/counts" "$RES"
$PY analyse.py "$RES"
$PY stats_models.py "$WORK/src" "$RES"
$PY crosscheck.py "$WORK/src" "$REPO/counts" "$RES"

say "4/6 Sensitivity analysis and BASE versus BSAP (Milestone 4)"
$PY sensitivity.py "$WORK/src" "$RES"
$PY bsap_model.py "$WORK/full" "$RES"

say "5/6 JTratch cross-check (Milestone 4)"
J8="${JAVA8_HOME:-}"
[ -z "$J8" ] && [ -x /usr/libexec/java_home ] && J8=$(/usr/libexec/java_home -v 1.8 2>/dev/null || true)
[ -z "$J8" ] && J8=$(ls -d /usr/lib/jvm/java-8-* /usr/lib/jvm/*1.8.0* 2>/dev/null | head -1 || true)
if [ -z "$J8" ] || [ ! -x "$J8/bin/javac" ]; then
  echo "  no Java 8 JDK found: JTratch step SKIPPED (see antipatterns/run_jtratch.md)"
else
  [ -d "$WORK/JTratch" ] || git clone -q https://github.com/guipadua/JTratch.git "$WORK/JTratch"
  mkdir -p "$WORK/JTratch/bin" "$WORK/m2"
  "$J8/bin/javac" -nowarn -encoding UTF-8 -cp "$WORK/JTratch/lib/*" -d "$WORK/JTratch/bin" \
      $(find "$WORK/JTratch/src/main/java" -name '*.java' | grep -v /sample/) 2>&1 | grep -v '^Note' || true
  # JTratch reads sources as UTF-8; one Compress file is ISO-8859-1, so analyse a converted copy (same line numbers)
  rm -rf "$WORK/compress_utf8"; cp -R "$WORK/full/compress/src/main/java" "$WORK/compress_utf8"
  for f in $(find "$WORK/compress_utf8" -name '*.java'); do
    iconv -f UTF-8 -t UTF-8 "$f" >/dev/null 2>&1 || { iconv -f ISO-8859-1 -t UTF-8 "$f" > "$f.tmp" && mv "$f.tmp" "$f"; }
  done
  run() {  # lib source-dir
    rm -rf "$WORK/jt_out/$1"; mkdir -p "$WORK/jt_out/$1"
    (cd "$WORK/jt_out/$1" && "$J8/bin/java" -Dfile.encoding=ISO-8859-1 -Xmx3g \
       -cp "$WORK/JTratch/bin:$WORK/JTratch/lib/*" ca.concordia.jtratch.JTratch ByFolder "$2" "$WORK/m2" >/dev/null 2>&1)
  }
  run lang     "$WORK/full/lang/src/main/java"
  run codec    "$WORK/full/codec/src/main/java"
  run compress "$WORK/compress_utf8"
  run gson     "$WORK/full/gson/gson/src/main/java"
  for l in lang codec compress gson; do
    mkdir -p "$RES/jtratch/$l"
    sed "s#$WORK/##g" "$(ls "$WORK/jt_out/$l"/*_CatchBlock.csv | head -1)" > "$RES/jtratch/$l/java_CatchBlock.csv"
  done
  $PY "$AP/jtratch_crosscheck.py" "$RES/jtratch" "$RES"
fi

say "6/6 Check the regenerated results against the numbers in the reports"
$PY "$AP/check_results.py" "$RES" "$AP/results"
