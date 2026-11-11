#!/usr/bin/env python3
"""Build the manual-check sheet: 30 flagged blocks (precision) + 10 unflagged blocks (misses).
Usage: make_sheet.py SRC_DIR OUT_DIR   (fixed random seed, so the sample is reproducible)"""
import sys
import pandas as pd

ROOT = {"Lang": "commons-lang", "Codec": "commons-codec", "Compress": "commons-compress", "Gson": "gson"}
PATS = ["generic_catch", "dummy_handler", "log_and_throw", "ignoring_interrupted"]


def source(src, r, before=1):
    path = f"{src}/{ROOT[r.library]}/{r.file}"
    lines = open(path, encoding="utf8", errors="replace").read().splitlines()
    return "\n".join(lines[max(0, r.line - 1 - before): r.end_line])


def main(src, out):
    b = pd.read_csv(f"{out}/blocks.csv")
    b["flag_list"] = b[PATS].apply(lambda r: ", ".join(p for p in PATS if r[p]), axis=1)
    flagged, unflagged = b[b.flag_list != ""], b[b.flag_list == ""]
    # rare patterns first (all of them), then random fill per flag type
    pick = flagged[flagged.ignoring_interrupted == 1]
    pick = pd.concat([pick, flagged[(flagged.statements > 0) & (flagged.dummy_handler == 1)]])
    rest = flagged.drop(pick.index)
    dummy = rest[rest.dummy_handler == 1].sample(n=min(13, (rest.dummy_handler == 1).sum()), random_state=42)
    generic = rest.drop(dummy.index)
    generic = generic[generic.generic_catch == 1].sample(n=30 - len(pick) - len(dummy), random_state=42)
    sample = pd.concat([pick, dummy, generic]).head(30)
    sample = sample.assign(part="A. flagged (precision)")
    miss = unflagged.sample(n=10, random_state=42).assign(part="B. not flagged (misses)")
    sheet = pd.concat([sample, miss]).reset_index(drop=True)
    sheet.insert(0, "id", range(1, len(sheet) + 1))
    sheet["code"] = [source(src, r) for r in sheet.itertuples()]
    sheet["detector_says"] = sheet.flag_list.replace("", "none")
    sheet["file"] = sheet.library + ": " + sheet.file.str.split("/").str[-1] + ":" + sheet.line.astype(str)
    sheet["correct_yes_no"] = ""
    sheet["reviewer_initials"] = ""
    sheet["notes"] = ""
    cols = ["id", "part", "file", "detector_says", "code", "correct_yes_no", "reviewer_initials", "notes"]
    sheet[cols].to_csv(f"{out}/manual_check_sheet.csv", index=False)
    with pd.ExcelWriter(f"{out}/manual_check_sheet.xlsx", engine="openpyxl") as w:
        sheet[cols].to_excel(w, index=False, sheet_name="check")
        ws = w.sheets["check"]
        for col, width in zip("ABCDEFGH", (5, 24, 40, 30, 90, 16, 10, 40)):
            ws.column_dimensions[col].width = width
        from openpyxl.styles import Alignment
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
    print(sheet.part.value_counts().to_dict(), "| flags in A:", sample.flag_list.value_counts().to_dict())


if __name__ == "__main__":
    main(*sys.argv[1:3])
