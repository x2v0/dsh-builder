#!/usr/bin/env python3
import os, sys, subprocess, json, shutil, glob
os.chdir(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))

flock_c = "native/system/packages/entry/src/flock.c"
out_dir = "node_modules/@deepseek-ai/node-addon-system-android-arm64/bin/bionic"
os.makedirs(out_dir, exist_ok=True)
out_node = os.path.join(out_dir, "system.node")

node_include = None
_node_real = os.path.realpath(shutil.which("node") or "/usr/bin/node")
for c in [
    os.path.join(os.path.dirname(os.path.dirname(_node_real)), "include", "node"),
    "/usr/include/node",
    "/usr/local/include/node",
]:
    if os.path.exists(os.path.join(c, "node_api.h")):
        node_include = c
        break
if not node_include:
    for g in glob.glob(os.path.expanduser("~/.cache/node-gyp/*/include/node")):
        if os.path.exists(os.path.join(g, "node_api.h")):
            node_include = g
            break
if not node_include:
    sys.exit("[-] node_api.h not found")
print(f"[+] node headers: {node_include}")

ndk = os.environ.get("ANDROID_NDK_HOME") or os.environ.get("ANDROID_NDK_ROOT") or ""
if not ndk:
    for p in ["/usr/local/lib/android/sdk/ndk",
              os.path.expanduser("~/android-sdk/ndk"),
              os.path.expanduser("~/.android/sdk/ndk")]:
        if os.path.isdir(p):
            vers = sorted(os.listdir(p))
            if vers:
                ndk = os.path.join(p, vers[-1])
                break
if not ndk:
    sys.exit("[-] NDK not found")

cc = os.path.join(ndk, "toolchains", "llvm", "prebuilt", "linux-x86_64", "bin",
                  "aarch64-linux-android30-clang")
if not os.path.exists(cc):
    sys.exit(f"[-] compiler not found: {cc}")
print(f"[+] NDK clang: {cc}")

cmd = [cc, "--target=aarch64-linux-android30", "-shared", "-fPIC", "-o", out_node,
       flock_c, f"-I{node_include}", "-D__ANDROID__", "-Wl,-z,nodelete"]
print(f"[*] {' '.join(cmd)}")
subprocess.run(cmd, check=True)

pkg_dir = "node_modules/@deepseek-ai/node-addon-system-android-arm64"
os.makedirs(pkg_dir, exist_ok=True)
with open(os.path.join(pkg_dir, "package.json"), "w") as f:
    json.dump({
        "name": "@deepseek-ai/node-addon-system-android-arm64",
        "version": "0.1.2",
        "main": "bin/bionic/system.node",
    }, f, indent=2)

info = subprocess.run(["file", out_node], capture_output=True, text=True).stdout.strip()
print(f"[+] {out_node}: {info}")
if not any(x in info for x in ("aarch64", "ARM aarch64", "ARM64")):
    sys.exit(f"[ERROR] system.node is not arm64: {info}")
print("[+] done")
