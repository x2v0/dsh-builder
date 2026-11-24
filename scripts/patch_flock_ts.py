#!/usr/bin/env python3
import os, sys
os.chdir(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
f = "native/system/packages/entry/src/flock.ts"
s = open(f).read()
old = "if (platform !== 'linux' && platform !== 'darwin') {"
new = "if (platform !== 'linux' && platform !== 'darwin' && platform !== 'android') {"
if old not in s:
    sys.exit(f"[-] anchor not found: {f}")
open(f, "w").write(s.replace(old, new, 1))
print(f"[+] patched {f}")
