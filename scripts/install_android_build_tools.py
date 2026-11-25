#!/usr/bin/env python3
"""Install Android-native build tools (esbuild, rolldown) for android-arm64.
Idempotent, no regex. Wires android-arm64 binaries into pnpm isolated
layout so esbuild main.js resolver finds them at runtime."""
import os, glob, subprocess

ROOT = os.getcwd()
PNPM = os.path.join(ROOT, "node_modules", ".pnpm")

def run(cmd):
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=False)

def esbuild_versions():
    out = []
    for p in glob.glob(os.path.join(PNPM, "esbuild@*")):
        ver = os.path.basename(p).split("@", 1)[1]
        out.append((p, ver))
    return out

def install_esbuild_android():
    total = len(esbuild_versions())
    ok = 0
    for esbuild_dir, ver in esbuild_versions():
        target = os.path.join(esbuild_dir, "node_modules", "@esbuild", "android-arm64")
        if os.path.isdir(os.path.join(target, "bin")):
            print(f"[=] esbuild {ver}: already present")
            ok += 1
            continue
        print(f"[*] esbuild {ver}: install @esbuild/android-arm64@{ver}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        run(["npm", "install", "--no-save", "--prefix",
             esbuild_dir, f"@esbuild/android-arm64@{ver}"])
        if os.path.isdir(os.path.join(target, "bin")):
            print(f"[+] esbuild {ver}: OK")
            ok += 1
        else:
            print(f"[!] esbuild {ver}: MISS at {target}")
    print(f"[=] esbuild: {ok}/{total} wired")

def install_rolldown_android():
    for rd in glob.glob(os.path.join(PNPM, "rolldown@*")):
        ver = os.path.basename(rd).split("@", 1)[1]
        dest = os.path.join(rd, "node_modules", "@rolldown", "binding-android-arm64")
        if os.path.isdir(dest):
            print(f"[=] rolldown {ver}: present")
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        run(["npm", "install", "--no-save", "--prefix",
             rd, "@rolldown/binding-android-arm64"])

def verify():
    for esbuild_dir, ver in esbuild_versions():
        b = os.path.join(esbuild_dir, "node_modules", "@esbuild", "android-arm64", "bin", "esbuild")
        tag = "[OK] " if os.path.exists(b) else "[MISS] "
        print(tag + f"esbuild {ver}")

if __name__ == "__main__":
    install_esbuild_android()
    install_rolldown_android()
    verify()
