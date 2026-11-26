# GitHub Actions 构建指南

本文档说明我们的构建流水线如何工作，如何运行它，
如何监控进度，以及如何验证完成的构建产物。

## 1. 什么是 GitHub Actions？

**GitHub Actions** 是 GitHub 内置的 CI/CD（持续集成 / 持续部署）系统。
它允许您在虚拟机上（运行器）在云中运行代码，无需您的参与。

对我们来说，这意味着：
*   我们不在手机上构建 DSH（慢、耗电、吃内存）。
*   相反，我们将代码推送到 GitHub，它在强大的服务器上启动构建
    （Ubuntu，7 GB RAM，2 核）。
*   结果（构建产物）下载到手机即可使用。

## 2. 什么是 `workflow.yaml`？

**`workflow.yaml`**（在我们的例子中是 `.github/workflows/build-dsh.yml`）是
GitHub Actions 的指令。它描述：
*   **何时运行**（`on: workflow_dispatch` — 手动，`on: push` — 提交时）。
*   **做什么**（步骤：`Checkout`、`Install`、`Build`、`Patch`、`Package`）。
*   **从哪里获取代码**（`deepseek-ai/deepseek-harness`）。
*   **把结果放在哪里**（构建产物 `dsh-android-arm64.tar.gz`）。

## 3. 分步说明

### 3.1. 如何编辑 YAML

所有编辑 — 仅通过 `python3 - << 'EOF'`（规则 #0）。不使用 `sed` 或手动 `nano`，
以避免破坏缩进。

示例：向 YAML 添加步骤：
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

### 3.2. 如何启动构建

```bash
cd ~/dsh-builder
git add .github/workflows/build-dsh.yml scripts/ patches/
git commit -m "feat: my changes"
git push
gh workflow run build-dsh.yml
```

### 3.3. 如何监控进度

```bash
cd ~/dsh-builder
gh run watch
```

或列出最近的运行：
```bash
gh run list -L 5
```

### 3.4. 如何下载构建产物

当构建完成（绿色对勾）时，运行：
```bash
cd ~/dsh-builder
gh run download <ID>
```
其中 `<ID>` 是运行编号（在 `gh run list` 中可见）。

构建产物出现在 `dsh-android-arm64/dsh-android-arm64.tar.gz`。

### 3.5. 如何验证完整性

解包后，检查所有原生模块是否到位：
```bash
cd ~/dsh-artifact
find . -name '*.node' | while read f; do printf '%s\t' "$f"; file "$f" | grep -oE 'ARM aarch64|x86-64|Android [0-9]+'; done
```
所有 `.node` 文件必须是 `ARM aarch64`。如果您看到 `x86-64` — 构建拉取了
主机版本，您需要修复脚本。

### 3.6. 如何运行构建产物

```bash
cd ~/dsh-artifact
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="sk-..."
node --import tsx/esm apps/cli/src/bin.ts web
```
如果服务器已启动 — 您将看到链接 `http://127.0.0.1:3080/?token=...`。
在浏览器中打开它。

## 4. 如果失败怎么办

1.  检查错误日志：
    ```bash
    gh run view --log-failed
    ```
2.  找到失败所在的步骤（`Build DSH`、`Compile system.node` 等）。
3.  如果错误在 `python` 脚本中 — 在 `scripts/` 中修复它。
4.  如果错误在 YAML 中 — 修复 `.github/workflows/build-dsh.yml`。
5.  推送更改并重新运行。

## 5. 有用链接

*   [GOALS.zh.md](GOALS.zh.md) — 项目目标。
*   [RULES.zh.md](RULES.zh.md) — 编辑规则。
*   [RESURECT.zh.md](RESURECT.zh.md) — 如何从头继续。

## 6. 实际工作示例

以下是我们构建 DSH 时使用的真实命令。
您可以复制并改编它们以满足您的需求。

### 6.1. 完整循环：编辑、提交、推送、运行、监控

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

### 6.2. 使用文件中的密钥运行构建产物

```bash
cd ~ && umask 077 && printf '%s' 'sk-NEW_KEY' > ~/.deepseek_key && chmod 600 ~/.deepseek_key
cd ~/dsh-final9/dsh-test9/dist-artifact
export DSH_HOME="$HOME/.dsh-sessions"
export DEEPSEEK_API_KEY="$(cat ~/.deepseek_key)"
timeout 120 node --import tsx/esm apps/cli/src/bin.ts web 2>&1 | tee ~/launch9.log
```

### 6.3. 检查脚本是否在提交中

```bash
cd ~/dsh-builder && git ls-files scripts/patch_flock_path_android.py scripts/patch_session_persistence.py
```

如果命令没有输出 — 文件未添加到 git，CI 将看不到它们。
