#!/usr/bin/env python3
import os, sys
os.chdir(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
pb = "apps/cli/src/profile-boot.ts"
if not os.path.exists(pb):
    sys.exit(f"[-] not found: {pb}")
lines = open(pb, encoding="utf-8").readlines()
changed = 0
for i, line in enumerate(lines):
    if "ctx.fiber.state === FiberState.ACTIVE" in line:
        lines[i] = line.replace("FiberState.ACTIVE", "2")
        changed += 1
open(pb, "w", encoding="utf-8").writelines(lines)
print(f"[+] replaced FiberState.ACTIVE: {changed}")
if changed == 0:
    sys.exit("[-] nothing replaced")
