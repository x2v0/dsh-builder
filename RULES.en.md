# Project Rules

## #0 — Python heredoc
All patches via `python3 - << 'EOF'`. Do not use `sed`, `awk`, `perl` to modify files.

## #1 — `cd` on the first line
Every patch starts with `cd <dir>`. Do not depend on the current path.

## #2 — No regexp
Avoid regular expressions. Use Python to add/replace lines (line by line, by exact substring match).

## #3 — Diagnose, don't guess
Before fixing — `ls`, `grep`, `cat` to see exactly what is missing.

## #4 — Don't break what works
Extend functionality, don't replace existing (e.g., add `android` to the platform list, don't replace `process.platform`).

## #5 — One step, one output
After each command, send the result to avoid accumulating errors.

## #6 — Fix the cause, not the symptom
For example, `tar --hard-dereference` instead of manually restoring each file.

## #7 — Check integrity
After unpacking — `ls node_modules/.bin`, `ls node_modules/.pnpm | wc -l` to ensure critical packages are in place.

## #8 — Debug web server
Use `--no-open` and `--trusted-host` for debugging the web server, to avoid depending on the browser.

## #11 — Line-by-line patches
Patches line by line, showing changed lines.

## #13 — Extend, don't replace
Add `android` to the platform list (via `NARB_TARGET_OS`), don't replace `process.platform` (otherwise Linux/Darwin/Win32 break).

## #111 — Everything in YAML
Move all local patches to YAML (GitHub Actions), so the artifact is built without manual edits.

## #555 — Termux
All commands are executed in Termux. Do not use `/tmp`, do not go outside `~/`.

## #12 — Text files: python add line

For purely text files (`.md`, `README`, `*.txt`, `*.yaml`-comments, etc.) **do not** write the content
as a single line and **do not** use `cat > file << EOF` with text inside heredoc. Instead, add text
**line by line** via `python3`: list of strings -> `f.writelines(...)`.

Reason: in Termux long strings with quotes, slashes, `$`, `` ` ``, `\` and unicode break when passed
through shell/heredoc. Line-by-line writing via python preserves every character as is.

Template:

```bash
cd <dir> && python3 - << 'PYEOF'
import io
lines = [
    "# Header\n",
    "\n",
    "Text with quotes \"...\", with slashes /path/to, $VAR, `cmd`.\n",
]
with io.open("FILE.md", "a", encoding="utf-8") as f:
    f.writelines(lines)
print("[+] appended", len(lines), "lines")
PYEOF
```

The rule applies to: `RESURECT.md`, `GOALS.md`, `RULES.md`, any README and text artifacts.
