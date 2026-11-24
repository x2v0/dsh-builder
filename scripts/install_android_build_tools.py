#!/usr/bin/env python3
"""Install Android-native build tools (esbuild, rolldown) for android-arm64.

TODO (пункт 2 стратегии): заменить скачивание prebuilt на сборку из исходников.
"""
import os, sys, urllib.request, tarfile, shutil, subprocess

# Правило #1: cd первой строкой
os.chdir(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))

ver = "0.28.1"
url = f"https://registry.npmjs.org/@esbuild/android-arm64/-/android-arm64-{ver}.tgz"
tgz = "esbuild-android.tgz"
dest = ".esbuild-android"
urllib.request.urlretrieve(url, tgz)
if os.path.exists(dest):
    shutil.rmtree(dest)
os.makedirs(dest)
with tarfile.open(tgz, "r:gz") as tar:
    tar.extractall(path=dest)
bin_path = os.path.join(dest, "package", "bin", "esbuild")
os.chmod(bin_path, 0o755)
print(f"[+] esbuild: {bin_path} (не запускаем на Linux)")

subprocess.run(
    ["npm", "install", "--no-save", "--force", "--no-package-lock",
     "@rolldown/binding-android-arm64"],
    check=False,
)
print("[+] rolldown binding installed (prebuilt, TODO: build from source)")
