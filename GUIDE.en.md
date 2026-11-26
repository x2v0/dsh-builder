# GitHub Actions Build Guide

**[🇷🇺 Русский](GUIDE.md) | [🇬🇧 English](GUIDE.en.md) | [🇨🇳 中文](GUIDE.zh.md)**


This document explains how our build pipeline works, how to run it,
how to monitor progress, and how to verify the finished artifact.

## 1. What is GitHub Actions?

**GitHub Actions** is a built-in CI/CD (Continuous Integration / Continuous Deployment)
system. It runs code on virtual machines (runners) in the cloud without your involvement.

For us, this means:
*   We do not build DSH on the phone (slow, drains battery, eats RAM).
*   Instead, we push code to GitHub, and it starts the build on a powerful server
    (Ubuntu, 7 GB RAM, 2 cores).
*   The result (artifact) is downloaded to the phone ready to use.

## 2. What is `workflow.yaml`?

**`workflow.yaml`** (in our case `.github/workflows/build-dsh.yml`) is the
instruction for GitHub Actions. It describes:
*   **When to run** (`on: workflow_dispatch` — manually, `on: push` — on commit).
*   **What to do** (steps: `Checkout`, `Install`, `Build`, `Patch`, `Package`).
*   **Where to get the code** (`deepseek-ai/deepseek-harness`).
*   **Where to put the result** (artifact `dsh-android-arm64.tar.gz`).

## 3. Step-by-step instructions

### 3.1. How to edit YAML

All edits — only via `python3 - << 'EOF'` (Rule #0). No `sed` or manual `nano`,
to avoid breaking indentation.

Example: add a step to YAML:
```bash
cd ~/dsh-builder
python3 - << 'EOF'
import os
file_path = '.github/workflows/build-dsh.yml'
with open(file_path, 'r') as f:
    content = f.read()
old = '''      - name: Install dependencies
        run: pnpm install --frozen-lockfile
'''
new = '''      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: My new step
        run: echo 'Hello'
'''
content = content.replace(old, new)
with open(file_path, 'w') as f:
    f.write(content)
print('[+] Step added.')
EOF
```

### 3.2. How to start a build

```bash
cd ~/dsh-builder
git add .github/workflows/build-dsh.yml scripts/ patches/
git commit -m "feat: my changes"
git push
gh workflow run build-dsh.yml
```

### 3.3. How to monitor progress

```bash
cd ~/dsh-builder
gh run watch
```

Or list recent runs:
```bash
gh run list -L 5
```

### 3.4. How to download the artifact

When the build finishes (green checkmark), run:
```bash
cd ~/dsh-builder
gh run download <ID>
```
Where `<ID>` is the run number (visible in `gh run list`).

The artifact appears in `dsh-android-arm64/dsh-android-arm64.tar.gz`.

### 3.5. How to verify integrity

After unpacking, check that all native modules are in place:
```bash
cd ~/dsh-artifact
find . -name '*.node' | while read f; do printf '%s\t' "$f"; file "$f" | grep -oE 'ARM aarch64|x86-64|Android [0-9]+'; done
```
All `.node` files must be `ARM aarch64`. If you see `x86-64` — the build pulled
the host version, and you need to fix the script.

### 3.6. How to run the artifact

```bash
cd ~/dsh-artifact
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="sk-..."
node --import tsx/esm apps/cli/src/bin.ts web
```
If the server started — you will see a link `http://127.0.0.1:3080/?token=...`.
Open it in your browser.

## 4. What to do if it fails

1.  Check the error log:
    ```bash
    gh run view --log-failed
    ```
2.  Find the step where it failed (`Build DSH`, `Compile system.node`, etc.).
3.  If the error is in a `python` script — fix it in `scripts/`.
4.  If the error is in YAML — fix `.github/workflows/build-dsh.yml`.
5.  Push changes and rerun.

## 5. Useful links

*   [GOALS.en.md](GOALS.en.md) — project goals.
*   [RULES.en.md](RULES.en.md) — editing rules.
*   [RESURECT.en.md](RESURECT.en.md) — how to continue from scratch.

## 6. Examples from real work

Below are real commands we used while building DSH.
You can copy and adapt them for your needs.

### 6.1. Full cycle: edit, commit, push, run, monitor

```bash
cd ~/dsh-builder && \
  rm -f README.md.bak4 && \
  git add .github/workflows/build-dsh.yml scripts/patch_flock_path_android.py scripts/patch_session_persistence.py && \
  git status --short && \
  git commit -m "ci: wire patch_flock_path_android + patch_session_persistence into build-dsh.yml" && \
  git push
sleep 5
cd ~/dsh-builder && for i in 1 2 3 4 5; do
  if gh workflow run build-dsh.yml; then echo "[OK] dispatched (try $i)"; break; fi
  echo "[retry $i] HTTP 500, sleep 15"; sleep 15
done
sleep 15
cd ~/dsh-builder && gh run list --limit 1 --json databaseId,status,conclusion
```

### 6.2. Running the built artifact with a key from a file

```bash
cd ~ && umask 077 && printf '%s' 'sk-NEW_KEY' > ~/.deepseek_key && chmod 600 ~/.deepseek_key
cd ~/dsh-final9/dsh-test9/dist-artifact
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="$(cat ~/.deepseek_key)"
timeout 120 node --import tsx/esm apps/cli/src/bin.ts web 2>&1 | tee ~/launch9.log
```

### 6.3. Checking that scripts are in the commit

```bash
cd ~/dsh-builder && git ls-files scripts/patch_flock_path_android.py scripts/patch_session_persistence.py
```

If the command outputs nothing — the files are not added to git, and CI won't see them.
