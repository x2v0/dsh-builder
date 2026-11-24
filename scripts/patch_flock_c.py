#!/usr/bin/env python3
import os, sys
os.chdir(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
f = "native/system/packages/entry/src/flock.c"
if not os.path.exists(f):
    sys.exit(f"[-] not found: {f}")
s = open(f).read()
old = "request->error = flock(request->fd, LOCK_EX | LOCK_NB) == 0 ? 0 : errno;"
new = "\n".join([
    "    struct flock fl;",
    "    fl.l_type = F_WRLCK;",
    "    fl.l_whence = SEEK_SET;",
    "    fl.l_start = 0;",
    "    fl.l_len = 0;",
    "    request->error = fcntl(request->fd, F_SETLK, &fl) == 0 ? 0 : errno;",
    "",
])
if old not in s:
    sys.exit(f"[-] anchor not found: {f}")
s = s.replace(old, new, 1)
if "#include <fcntl.h>" not in s:
    s = s.replace("#include <sys/file.h>", "#include <sys/file.h>\n#include <fcntl.h>")
open(f, "w").write(s)
print(f"[+] patched {f}")
