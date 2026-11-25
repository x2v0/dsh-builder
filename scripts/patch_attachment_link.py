#!/usr/bin/env python3
"""Patch attachment-local: link() -> copyFile/rename fallback for Android bionic.
Idempotent. No regex. Anchors on exact substrings from shipped lib/index.js."""
import io, os, sys

TARGET = "packages/attachment/attachment-local/lib/index.js"

def patch(path):
    with io.open(path, encoding="utf-8") as f:
        lines = f.readlines()
    out = []
    i = 0
    n = len(lines)
    changed = 0
    while i < n:
        line = lines[i]
        s = line.strip()
        # SITE A: publishImmutableAlias -> copyFile fallback
        if s == "await link(source, target);":
            if any("termux-hardlink-fallback" in x for x in out[-3:]):
                out.append(line); i += 1; continue
            indent = line[:len(line) - len(line.lstrip())]
            out.append(indent + '/* termux-hardlink-fallback: bionic link() may EPERM/ENOSYS; copy instead (source stays immutable) */\n')
            out.append(indent + 'try {\n')
            out.append(indent + '    await link(source, target);\n')
            out.append(indent + '} catch (error) {\n')
            out.append(indent + '    if (!(error instanceof Error && "code" in error && (error.code === "EPERM" || error.code === "ENOSYS" || error.code === "EACCES"))) throw error;\n')
            out.append(indent + '    await copyFile(source, target);\n')
            out.append(indent + '}\n')
            changed += 1
            i += 1
            continue
        # SITE B: publishStagedObject -> rename fallback + guarded unlink
        if s == "await link(staged.path, target);":
            if any("termux-hardlink-fallback" in x for x in out[-3:]):
                out.append(line); i += 1; continue
            indent = line[:len(line) - len(line.lstrip())]
            out.append(indent + '/* termux-hardlink-fallback: bionic link() may EPERM/ENOSYS; rename moves staged into place */\n')
            out.append(indent + 'let linked = true;\n')
            out.append(indent + 'try {\n')
            out.append(indent + '    await link(staged.path, target);\n')
            out.append(indent + '} catch (error) {\n')
            out.append(indent + '    if (!(error instanceof Error && "code" in error && (error.code === "EPERM" || error.code === "ENOSYS" || error.code === "EACCES"))) throw error;\n')
            out.append(indent + '    await rename(staged.path, target);\n')
            out.append(indent + '    linked = false;\n')
            out.append(indent + '}\n')
            changed += 1
            i += 1
            continue
        if s == "await unlink(staged.path);":
            if any("linked = false" in x for x in out[-15:]):
                indent = line[:len(line) - len(line.lstrip())]
                out.append(indent + '/* termux-hardlink-fallback: skip unlink if rename already moved staged */\n')
                out.append(indent + 'if (linked) await unlink(staged.path);\n')
                i += 1
                continue
            out.append(line); i += 1; continue
        out.append(line)
        i += 1
    with io.open(path, "w", encoding="utf-8") as f:
        f.writelines(out)
    return changed

if __name__ == "__main__":
    c = patch(TARGET)
    print(f"[+] patched {c} sites in {TARGET}")
