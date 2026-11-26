# 项目规则

**[🇷🇺 Русский](RULES.md) | [🇬🇧 English](RULES.en.md) | [🇨🇳 中文](RULES.zh.md)**


## #0 — Python heredoc
所有补丁通过 `python3 - << 'EOF'`。不要使用 `sed`、`awk`、`perl` 修改文件。

## #1 — 第一行 `cd`
每个补丁以 `cd <dir>` 开头。不要依赖当前路径。

## #2 — 无正则表达式
避免正则表达式。使用 Python 添加/替换行（逐行，按精确子字符串匹配）。

## #3 — 诊断，不猜测
修复前 — `ls`、`grep`、`cat` 查看到底缺少什么。

## #4 — 不要破坏可用的东西
扩展功能，不要替换现有的（例如，将 `android` 添加到平台列表，不要替换 `process.platform`）。

## #5 — 一步一输出
每条命令后发送结果，以避免错误累积。

## #6 — 修复原因，不是症状
例如，`tar --hard-dereference` 而不是手动恢复每个文件。

## #7 — 检查完整性
解包后 — `ls node_modules/.bin`、`ls node_modules/.pnpm | wc -l` 以确保关键包到位。

## #8 — 调试 Web 服务器
使用 `--no-open` 和 `--trusted-host` 调试 Web 服务器，以避免依赖浏览器。

## #11 — 逐行补丁
逐行打补丁，显示更改的行。

## #13 — 扩展，不替换
将 `android` 添加到平台列表（通过 `NARB_TARGET_OS`），不要替换 `process.platform`（否则 Linux/Darwin/Win32 会坏）。

## #111 — 一切在 YAML 中
将所有本地补丁移到 YAML（GitHub Actions），以便构建产物无需手动编辑即可构建。

## #555 — Termux
所有命令在 Termux 中执行。不要使用 `/tmp`，不要超出 `~/`。

## #12 — 文本文件：python 逐行添加

对于纯文本文件（`.md`、`README`、`*.txt`、`*.yaml`-注释等）**不要**将内容写成
一行，**不要**使用带 heredoc 内文本的 `cat > file << EOF`。相反，通过 `python3`
**逐行**添加文本：字符串列表 -> `f.writelines(...)`。

原因：在 Termux 中，带引号、斜杠、`$`、`` ` ``、`\` 和 unicode 的长字符串在通过
shell/heredoc 传递时会断裂。通过 python 逐行写入会原样保留每个字符。

模板：

```bash
cd <dir> && python3 - << 'PYEOF'
import io
lines = [
    "# 标题\n",
    "\n",
    "带引号 \"...\" 的文本，带斜杠 /path/to，$VAR，`cmd`。\n",
]
with io.open("FILE.md", "a", encoding="utf-8") as f:
    f.writelines(lines)
print("[+] appended", len(lines), "lines")
PYEOF
```

该规则适用于：`RESURECT.md`、`GOALS.md`、`RULES.md`、任何 README 和文本产物。
