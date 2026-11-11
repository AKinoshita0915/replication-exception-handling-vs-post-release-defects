#!/usr/bin/env python3
"""Catch-block anti-pattern detector (Generic Catch, Dummy Handler, Log and Throw,
Ignoring Interrupted Exception) following the ICPC 2017 definitions of de Padua and Shang.

Usage: detect.py SRC_DIR COUNTS_DIR OUT_DIR
  SRC_DIR    folder holding the four checked-out libraries (commons-lang, commons-codec,
             commons-compress, gson) at their release tags
  COUNTS_DIR the 'counts' folder of the group repository (catch / fixed file lists)
  OUT_DIR    where blocks.csv and files.csv are written
"""
import csv
import os
import sys

import tree_sitter_java as tsj
from tree_sitter import Language, Parser

LIBS = {  # name -> (checkout folder, list prefix)
    "Lang": ("commons-lang", "lang"),
    "Codec": ("commons-codec", "codec"),
    "Compress": ("commons-compress", "compress"),
    "Gson": ("gson", "gson"),
}
GENERIC = {"Exception", "Throwable"}
LOGGER_NAMES = {"log", "logger", "logging", "slf4j", "log4j"}
PRINT_METHODS = {"print", "println", "printf", "format"}
PARSER = Parser(Language(tsj.language()))


def text(node):
    return node.text.decode("utf8", "replace")


def descendants(node):
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)


def catch_types(clause):
    """Simple names of the exception types caught by one catch clause."""
    param = next((c for c in clause.children if c.type == "catch_formal_parameter"), None)
    if param is None:
        return []
    ctype = next((c for c in param.children if c.type == "catch_type"), None)
    names = []
    for c in (ctype.children if ctype else []):
        if c.type in ("type_identifier", "scoped_type_identifier"):
            names.append(text(c).split(".")[-1])
    return names


def is_logging_call(call):
    """A method call that logs or prints: logger.x(..), LOG.x(..), System.out/err.x(..), e.printStackTrace()."""
    name_node = call.child_by_field_name("name")
    obj = call.child_by_field_name("object")
    name = text(name_node) if name_node else ""
    if name == "printStackTrace":
        return True
    if obj is None:
        return False
    obj_txt = text(obj)
    if obj_txt in ("System.out", "System.err") and name in PRINT_METHODS:
        return True
    last = obj_txt.split(".")[-1].lower()
    return last in LOGGER_NAMES or last.endswith("logger") or last.endswith("log")


def statements(block):
    return [c for c in block.children if c.is_named and c.type not in ("line_comment", "block_comment")]


def stmt_is_logging(stmt):
    if stmt.type != "expression_statement":
        return False
    call = next((c for c in stmt.children if c.type == "method_invocation"), None)
    return call is not None and is_logging_call(call)


def analyse_clause(clause):
    types = catch_types(clause)
    body = clause.child_by_field_name("body") or next((c for c in clause.children if c.type == "block"), None)
    stmts = statements(body) if body is not None else []
    nodes = list(descendants(body)) if body is not None else []
    has_throw = any(n.type == "throw_statement" for n in nodes)
    has_log = any(n.type == "method_invocation" and is_logging_call(n) for n in nodes)
    calls_interrupt = any(
        n.type == "method_invocation" and (n.child_by_field_name("name") is not None
                                           and text(n.child_by_field_name("name")) == "interrupt")
        for n in nodes
    )
    flags = {
        "generic_catch": any(t in GENERIC for t in types),
        "dummy_handler": (len(stmts) == 0) or all(stmt_is_logging(s) for s in stmts),
        "log_and_throw": has_log and has_throw,
        "ignoring_interrupted": ("InterruptedException" in types) and not has_throw and not calls_interrupt,
    }
    return types, len(stmts), flags, body


def read_list(path):
    if not os.path.exists(path):
        return []
    return [l.strip() for l in open(path, encoding="utf8") if l.strip()]


def main(src_dir, counts_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    pats = ["generic_catch", "dummy_handler", "log_and_throw", "ignoring_interrupted"]
    block_rows, file_rows = [], []
    for lib, (folder, prefix) in LIBS.items():
        root = os.path.join(src_dir, folder)
        catch_files = read_list(os.path.join(counts_dir, f"{prefix}_catch_files.txt"))
        fixed = set(read_list(os.path.join(counts_dir, f"{prefix}_fixed_files.txt")))
        fixed_nl = set(read_list(os.path.join(counts_dir, f"{prefix}_fixed_files_nolimit.txt")))
        for rel in catch_files:
            path = os.path.join(root, rel)
            src = open(path, "rb").read()
            tree = PARSER.parse(src)
            file_flags = {p: 0 for p in pats}
            n_catch = 0
            for node in descendants(tree.root_node):
                if node.type != "catch_clause":
                    continue
                n_catch += 1
                types, n_stmt, flags, body = analyse_clause(node)
                for p in pats:
                    file_flags[p] += int(flags[p])
                snippet = " ".join(text(node).split())[:220]
                block_rows.append({
                    "library": lib, "file": rel, "line": node.start_point[0] + 1,
                    "end_line": node.end_point[0] + 1, "types": "|".join(types),
                    "statements": n_stmt, **{p: int(flags[p]) for p in pats}, "snippet": snippet,
                })
            file_rows.append({
                "library": lib, "file": rel, "catch_blocks": n_catch,
                "defective": int(rel in fixed), "defective_no_window_end": int(rel in fixed_nl),
                "parse_errors": int(tree.root_node.has_error),
                **{p: file_flags[p] for p in pats},
            })
    for name, rows in (("blocks.csv", block_rows), ("files.csv", file_rows)):
        with open(os.path.join(out_dir, name), "w", newline="", encoding="utf8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"{len(file_rows)} catch files, {len(block_rows)} catch blocks -> {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
