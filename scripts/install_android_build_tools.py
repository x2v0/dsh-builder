#!/usr/bin/env python3
"""Install @esbuild/android-arm64 and @rolldown/binding-android-arm64 into pnpm layout.
Direct registry download via urllib+tarfile — bypasses npm EBADPLATFORM that refuses
android-arm64 packages on linux-x64 CI host. Idempotent, no regex."""
import os, glob, json, tarfile, shutil, urllib.request

ROOT = os.getcwd()
PNPM = os.path.join(ROOT, "node_modules", ".pnpm")

def fetch_tgz(url, dest):
    print(f"[dl] {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "dsh-builder/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f)

def extract_pkg(tgz, target):
    os.makedirs(target, exist_ok=True)
    with tarfile.open(tgz, "r:gz") as tf:
        for m in tf.getmembers():
            if not m.name.startswith("package/"):
                continue
            rel = m.name[len("package/"):]
            if not rel:
                continue
            out = os.path.join(target, rel)
            if m.isdir():
                os.makedirs(out, exist_ok=True)
            elif m.isfile():
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with tf.extractfile(m) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                os.chmod(out, m.mode)

def esbuild_versions():
    out = []
    for p in glob.glob(os.path.join(PNPM, "esbuild@*")):
        ver = os.path.basename(p).split("@", 1)[1]
        out.append((p, ver))
    return out

def install_esbuild():
    total = len(esbuild_versions())
    ok = 0
    for esbuild_dir, ver in esbuild_versions():
        target = os.path.join(esbuild_dir, "node_modules", "@esbuild", "android-arm64")
        bin_path = os.path.join(target, "bin", "esbuild")
        if os.path.exists(bin_path):
            print(f"[=] esbuild {ver}: present")
            ok += 1
            continue
        url = f"https://registry.npmjs.org/@esbuild/android-arm64/-/android-arm64-{ver}.tgz"
        tgz = os.path.join(ROOT, f".esbuild-{ver}.tgz")
        try:
            fetch_tgz(url, tgz)
            extract_pkg(tgz, target)
            os.remove(tgz)
            if os.path.exists(bin_path):
                os.chmod(bin_path, 0o755)
                print(f"[+] esbuild {ver}: OK")
                ok += 1
            else:
                print(f"[!] esbuild {ver}: extracted but bin missing at {bin_path}")
        except Exception as e:
            print(f"[!] esbuild {ver}: {e}")
    print(f"[=] esbuild: {ok}/{total} wired")

def rolldown_binding_version(rd_dir):
    for pj in [
        os.path.join(rd_dir, "node_modules", "rolldown", "package.json"),
        os.path.join(rd_dir, "package.json"),
    ]:
        if os.path.exists(pj):
            try:
                with open(pj, encoding="utf-8") as f:
                    data = json.load(f)
                od = data.get("optionalDependencies", {})
                v = od.get("@rolldown/binding-android-arm64")
                if v:
                    return v.lstrip("^~=<>")
            except Exception:
                pass
    return None

def install_rolldown():
    for rd in glob.glob(os.path.join(PNPM, "rolldown@*")):
        ver = os.path.basename(rd).split("@", 1)[1]
        target = os.path.join(rd, "node_modules", "@rolldown", "binding-android-arm64")
        if os.path.isdir(target) and any(f.endswith(".node") for f in os.listdir(target)):
            print(f"[=] rolldown {ver}: present")
            continue
        bver = rolldown_binding_version(rd)
        if not bver:
            print(f"[!] rolldown {ver}: cannot determine binding version")
            continue
        url = f"https://registry.npmjs.org/@rolldown/binding-android-arm64/-/binding-android-arm64-{bver}.tgz"
        tgz = os.path.join(ROOT, f".rolldown-{ver}-{bver}.tgz")
        try:
            fetch_tgz(url, tgz)
            extract_pkg(tgz, target)
            os.remove(tgz)
            print(f"[+] rolldown {ver}: OK (binding {bver})")
        except Exception as e:
            print(f"[!] rolldown {ver}: {e}")

if __name__ == "__main__":
    install_esbuild()
    install_rolldown()
