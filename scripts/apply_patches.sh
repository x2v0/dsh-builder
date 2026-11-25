#!/usr/bin/env bash
set -euo pipefail

# Путь к корню репозитория DSH (в GitHub Actions это рабочая директория)
REPO_DIR="$(pwd)"
PKGS="$REPO_DIR/packages"

# В CI dsh-builder чекаутится в path: builder, поэтому patches/ лежат в builder/patches/.
# Локально (из ~/dsh-builder) — рядом: ./patches/.
if [ -d "$REPO_DIR/builder/patches" ]; then
    PATCHES_DIR="$REPO_DIR/builder/patches"
elif [ -d "$REPO_DIR/patches" ]; then
    PATCHES_DIR="$REPO_DIR/patches"
else
    echo "  [WARN] patches dir not found (neither builder/patches nor patches)"
    PATCHES_DIR="$REPO_DIR/patches"
fi

# apply_patch <patch-file> <package-dir>
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

apply_patch "$PATCHES_DIR/01-terminal-bash-android-shell.patch"        "$PKGS/terminal/terminal-bash"                 || true
apply_patch "$PATCHES_DIR/02-session-persistence-link-rename.patch"    "$PKGS/session/session-persistence-jsonl"      || true
apply_patch "$PATCHES_DIR/03-subprocess-local-android.patch"           "$PKGS/subprocess/subprocess-local"            || true
apply_patch "$PATCHES_DIR/05-host-directory-picker-native-android.patch" "$PKGS/host/directory-picker-native"         || true
apply_patch "$PATCHES_DIR/06-workspace-archive-skip-session-known-check.patch" "$PKGS/workspace/workspace"            || true
# apply_patch "$PATCHES_DIR/07-sandbox-local-proot-runner.patch"         "$PKGS/sandbox/sandbox-local"                  || true  # disabled: proot запрещён
apply_patch "$PATCHES_DIR/08-dsh-tool-fs-search-android-rg.patch"      "$PKGS/fs/tool-fs-search"                      || true

# Новые: hard-link fallback (аналог шагов 6/8 install.sh)
apply_patch "$PATCHES_DIR/09-attachment-local-link-rename.patch"       "$PKGS/attachment/attachment-local"            || true
apply_patch "$PATCHES_DIR/10-fs-local-link-rename.patch"              "$PKGS/fs/fs-local"                            || true

# 04: opener переехал host-apiproxy -> host/open-in-app; анкоры старые -> вероятен [SKIP]
apply_patch "$PATCHES_DIR/04-host-apiproxy-termux-open-index.patch"   "$PKGS/host/open-in-app"                       || true
apply_patch "$PATCHES_DIR/04-host-apiproxy-termux-open-opener.patch"  "$PKGS/host/open-in-app"                       || true

echo "=== Патчи применены ==="
