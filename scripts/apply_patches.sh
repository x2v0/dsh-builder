#!/usr/bin/env bash
set -euo pipefail

# Путь к корню репозитория DSH (в GitHub Actions это рабочая директория)
REPO_DIR="$(pwd)"
DSH_PKGS="$REPO_DIR/node_modules/@deepseek-ai"

# Функция для применения патча (аналог из install.sh)
apply_patch() {
    local patch="$1" dir="$2"
    if [ ! -f "$patch" ]; then
        echo "  [WARN] patch file missing: $patch"
        return 1
    fi
    if [ ! -d "$dir" ]; then
        echo "  [WARN] $(basename "$patch"): package dir not found ($dir) — skipping"
        return 1
    fi
    if (cd "$dir" && patch -p1 --dry-run --forward < "$patch" > /dev/null 2>&1); then
        (cd "$dir" && patch -p1 --forward < "$patch" > /dev/null 2>&1)
        echo "  [OK] $(basename "$patch") -> $(basename "$dir")"
        return 0
    fi
    echo "  [SKIP] $(basename "$patch") already applied or inapplicable ($dir)"
    return 1
}

echo "=== Применяем патчи Termux ==="

apply_patch "patches/01-terminal-bash-android-shell.patch" "$DSH_PKGS/dsh-terminal-bash" || true
apply_patch "patches/02-session-persistence-link-rename.patch" "$DSH_PKGS/dsh-session-persistence-jsonl" || true
apply_patch "patches/03-subprocess-local-android.patch" "$DSH_PKGS/dsh-subprocess-local" || true
apply_patch "patches/04-host-apiproxy-termux-open-index.patch" "$DSH_PKGS/dsh-host-apiproxy" || true
apply_patch "patches/04-host-apiproxy-termux-open-opener.patch" "$DSH_PKGS/dsh-host-apiproxy" || true
apply_patch "patches/05-host-directory-picker-native-android.patch" "$DSH_PKGS/dsh-host-directory-picker-native" || true
apply_patch "patches/06-workspace-archive-skip-session-known-check.patch" "$DSH_PKGS/dsh-workspace" || true
apply_patch "patches/07-sandbox-local-proot-runner.patch" "$DSH_PKGS/dsh-sandbox-local" || true
apply_patch "patches/08-dsh-tool-fs-search-android-rg.patch" "$DSH_PKGS/dsh-tool-fs-search" || true

# Патч koffi (он лежит в .pnpm)
KOFFI_DIR=$(find node_modules/.pnpm -maxdepth 1 -type d -name "koffi@*" | head -n 1)
if [ -n "$KOFFI_DIR" ]; then
    apply_patch "patches/koffi-statx.patch" "$KOFFI_DIR/node_modules/koffi" || true
else
    echo "  [WARN] koffi not found in .pnpm"
fi

echo "=== Патчи применены ==="
