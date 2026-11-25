#!/usr/bin/env python3
"""session-persistence-jsonl: add `rename` to node:fs/promises import.
Fixes ReferenceError: rename is not defined (патч 02 вставляет await rename(...)
без импорта). Idempotent, no regex, cd first (RULE #1)."""
import io, os

TARGET = "packages/session/session-persistence-jsonl/lib/index.js"

def patch(path):
    if not os.path.exists(path):
        print(f"[!] {path} not found")
        return 0
    with io.open(path, encoding="utf-8") as f:
        lines = f.readlines()
    changed = 0
    for i, line in enumerate(lines):
        s = line.rstrip("\n")
        if s.startswith("import {") and 'from "node:fs/promises"' in s and "rename" not in s.split('"')[0]:
            if "readFile, readdir, realpath," in s:
                s = s.replace("readFile, readdir, realpath,",
                              "readFile, readdir, realpath, rename,", 1)
                lines[i] = s + "\n"
                changed += 1
                print(f"[+] line {i+1}: rename added")
                break
    if changed:
        with io.open(path, "w", encoding="utf-8") as f:
            f.writelines(lines)
    return changed

if __name__ == "__main__":
    c = patch(TARGET)
    print(f"[+] patched {c} site(s) in {TARGET}")
