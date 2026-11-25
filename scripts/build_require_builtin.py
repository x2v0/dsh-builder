#!/usr/bin/env python3
"""Build require_builtin.node for android-arm64 on GitHub Actions (ubuntu-latest).

Two fixes vs previous version:
  1. NDK cross-compiler (CXX=aarch64-linux-android30-clang++) — previous version
     used host c++ → x86-64 binary landed in *-android-arm64/ folder.
  2. Dynamic version detection — previous version hardcoded 0.1.9, but pnpm
     installed 0.1.10, so loader could not find the file.

Idempotent, no regex, cd first (RULE #1)."""
import os, sys, glob, shutil, subprocess, json

try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

# RULE #1: cd first
work = os.environ.get("GITHUB_WORKSPACE") or os.getcwd()
os.chdir(work)
print(f"[cd] {work}")

UPSTREAM = "https://github.com/deepseek-ai/dsh-node-addon-require-builtin.git"


def find_installed_version():
    pats = glob.glob("node_modules/.pnpm/node-addon-require-builtin@*")
    if not pats:
        sys.exit("[-] node-addon-require-builtin not installed in node_modules/.pnpm")
    vers = []
    for p in pats:
        v = os.path.basename(p).split("@", 1)[1]
        # strip any pnpm suffix like _peer@x or _patch_hash=...
        v = v.split("_", 1)[0]
        vers.append(v)
    def key(s):
        return [int(x) if x.isdigit() else 0 for x in s.split(".")]
    vers.sort(key=key)
    return vers[-1]


def find_ndk():
    ndk = os.environ.get("ANDROID_NDK_HOME") or os.environ.get("ANDROID_NDK_ROOT") or ""
    if ndk and os.path.isdir(ndk):
        return ndk
    for p in ["/usr/local/lib/android/sdk/ndk",
              os.path.expanduser("~/android-sdk/ndk"),
              os.path.expanduser("~/.android/sdk/ndk")]:
        if os.path.isdir(p):
            vers = sorted([d for d in os.listdir(p)
                           if os.path.isdir(os.path.join(p, d))])
            if vers:
                return os.path.join(p, vers[-1])
    sys.exit("[-] NDK not found (ANDROID_NDK_HOME, ~/android-sdk/ndk)")


def npm_githead(pkg, ver):
    """Resolve exact git commit for a published npm version (best effort)."""
    url = f"https://registry.npmjs.org/{pkg}/{ver}"
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "dsh-builder/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        return data.get("gitHead")
    except Exception as e:
        print(f"[!] npm_githead({pkg}@{ver}) failed: {e}")
        return None


def clone_at_commit(commit, dest):
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    print(f"[*] clone commit {commit[:12] if commit else 'master'}")
    if commit:
        subprocess.run(["git", "clone", UPSTREAM, dest], check=True)
        r = subprocess.run(["git", "-C", dest, "checkout", commit], check=False)
        if r.returncode != 0:
            print(f"[!] checkout {commit[:12]} failed, staying on master")
    else:
        subprocess.run(["git", "clone", "--depth", "1", UPSTREAM, dest], check=True)


def strip_pm_pin(pkg_path):
    with open(pkg_path, encoding="utf-8") as f:
        data = json.load(f)
    if "packageManager" in data:
        removed = data.pop("packageManager")
        with open(pkg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[+] removed packageManager pin ({removed})")


def patch_pm_allow_builds(pkg_path):
    """pnpm 10+ refuses build scripts of dependencies unless approved.
    For trusted upstream in CI, allow all builds via package.json."""
    with open(pkg_path, encoding="utf-8") as f:
        data = json.load(f)
    pnpm = data.setdefault("pnpm", {})
    pnpm["dangerouslyAllowAllBuilds"] = True
    with open(pkg_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("[+] package.json: pnpm.dangerouslyAllowAllBuilds = true")


def patch_build_ts(build_ts):
    if not os.path.exists(build_ts):
        print("[!] scripts/build.ts not found")
        return
    with open(build_ts, encoding="utf-8") as f:
        content = f.read()
    changed = 0
    # 1) 'android' in platform whitelist
    if "'android'" not in content and '"android"' not in content:
        for anchor in ["'linux'", '"linux"']:
            if anchor in content:
                content = content.replace(anchor, anchor + ", 'android'", 1)
                changed += 1
                break
    # 2) runtimeSuffix() for android
    if "NARB_TARGET_OS" not in content:
        anchor = "function runtimeSuffix(): string {"
        if anchor in content:
            inject = (anchor +
                      "\n  if (process.env.NARB_TARGET_OS === 'android') "
                      "return `android-${process.env.NARB_TARGET_ARCH || 'arm64'}`;")
            content = content.replace(anchor, inject, 1)
            changed += 1
    with open(build_ts, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] build.ts patched ({changed} changes)")


def verify_arch(node_file):
    if not os.path.exists(node_file):
        return False, "file missing"
    r = subprocess.run(["file", node_file], capture_output=True, text=True)
    out = r.stdout
    if "aarch64" in out or "ARM aarch64" in out:
        return True, out.strip()
    return False, out.strip()


def main():
    ver = find_installed_version()
    print(f"[+] detected version: {ver}")

    ndk = find_ndk()
    print(f"[+] NDK: {ndk}")
    tool_bin = os.path.join(ndk, "toolchains", "llvm", "prebuilt", "linux-x86_64", "bin")
    cc  = os.path.join(tool_bin, "aarch64-linux-android30-clang")
    cxx = os.path.join(tool_bin, "aarch64-linux-android30-clang++")
    if not os.path.exists(cxx):
        sys.exit(f"[-] NDK clang++ not found at {cxx}")
    print(f"[+] CXX = {cxx}")

    clone = os.path.join(work, "dsh-node-addon-require-builtin")
    commit = npm_githead("node-addon-require-builtin", ver)
    print(f"[+] npm gitHead for {ver}: {commit or "(none)"}")
    clone_at_commit(commit, clone)

    strip_pm_pin(os.path.join(clone, "package.json"))
    patch_pm_allow_builds(os.path.join(clone, "package.json"))
    patch_build_ts(os.path.join(clone, "scripts", "build.ts"))

    # Install (host pnpm OK — clone runs on linux-x64 CI)
    print("[*] pnpm install --no-frozen-lockfile (allow-builds)")
    print("[*] clone: patching pnpm.dangerouslyAllowAllBuilds")
    if subprocess.run(["pnpm", "install", "--no-frozen-lockfile"],
                      cwd=clone).returncode != 0:
        sys.exit("[-] pnpm install failed")

    # Cross-compile with NDK
    env = os.environ.copy()
    env["npm_config_dangerously_allow_all_builds"] = "true"
    env["CC"]  = cc
    env["CXX"] = cxx
    env["AR"]  = os.path.join(tool_bin, "llvm-ar")
    env["LDFLAGS"] = "--target=aarch64-linux-android30"
    env["CFLAGS"]  = "--target=aarch64-linux-android30 -fPIC"
    env["CXXFLAGS"] = "--target=aarch64-linux-android30 -fPIC"
    env["NARB_TARGET_OS"]   = "android"
    env["NARB_TARGET_ARCH"] = "arm64"
    print("[*] pnpm build:native:napi (NDK cross-compile)")
    if subprocess.run(["pnpm", "build:native:napi"],
                      cwd=clone, env=env).returncode != 0:
        sys.exit("[-] build:native:napi failed")

    # Locate result
    candidates = [
        "packages/require-builtin/entry/build/napi/napi-v9-android-arm64/require_builtin.node",
        "packages/internal-loader/entry/build/napi/napi-v9-android-arm64/require_builtin.node",
    ]
    src = None
    for c in candidates:
        full = os.path.join(clone, c)
        if os.path.exists(full):
            src = full
            break
    if not src:
        for root, dirs, files in os.walk(os.path.join(clone, "packages")):
            if "require_builtin.node" in files and "napi" in root and "android" in root:
                src = os.path.join(root, "require_builtin.node")
                break
    if not src:
        sys.exit("[-] require_builtin.node not produced")

    ok, info = verify_arch(src)
    print(f"[arch] {src}")
    print(f"       {info}")
    if not ok:
        sys.exit("[-] built binary is not aarch64 — cross-compile did not apply")

    # Copy to pnpm's installed slot (detected version, both ABI dirs)
    pkg_base = os.path.join(
        "node_modules", ".pnpm",
        f"node-addon-require-builtin@{ver}",
        "node_modules", "node-addon-require-builtin", "build")
    dsts = [
        os.path.join(pkg_base, "napi",    "napi-v9-android-arm64"),
        os.path.join(pkg_base, "nodeabi", "node-v147-android-arm64"),
    ]
    for d in dsts:
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, "require_builtin.node")
        shutil.copyfile(src, dst)
        ok2, info2 = verify_arch(dst)
        flag = "[+]" if ok2 else "[!]"
        print(f"{flag} -> {dst}")
        print(f"       {info2}")
        if not ok2:
            sys.exit(f"[-] copied binary at {dst} is not aarch64")

    print(f"[+] done — version {ver}, aarch64")


if __name__ == "__main__":
    main()
