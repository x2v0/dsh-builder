#!/usr/bin/env python3
"""flock.js: for android, look for bin/bionic/system.node (build_system_node.py
places it there). Idempotent, no regex, cd first (RULE #1)."""
import io, os, sys

TARGET = "native/system/packages/entry/lib/flock.js"

def patch(path):
    if not os.path.exists(path):
        print(f"[!] {path} not found")
        return 0
    with io.open(path, encoding="utf-8") as f:
        lines = f.readlines()
    if any("termux-bionic-system-node" in l for l in lines):
        print("[=] already patched")
        return 0
    out = []
    changed = 0
    for line in lines:
        s = line.rstrip("\n")
        if s.strip() == "if (platform === 'linux') {":
            indent = s[:len(s) - len(s.lstrip())]
            out.append(indent + "/* termux-bionic-system-node: android uses bin/bionic/system.node */\n")
            out.append(indent + "if (platform === 'android') {\n")
            out.append(indent + "    filename = join('bionic', filename);\n")
            out.append(indent + "} else if (platform === 'linux') {\n")
            changed += 1
            continue
        out.append(s + "\n")
    with io.open(path, "w", encoding="utf-8") as f:
        f.writelines(out)
    return changed

if __name__ == "__main__":
    c = patch(TARGET)
    print(f"[+] patched {c} site(s) in {TARGET}")
