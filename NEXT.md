# NEXT.md — с чего начать (холодный старт)

## 1. Проверить статус
```bash
cd ~/dsh-builder
git status
git log --oneline -3
gh run list -L 3
```

## 2. Применить патчи в форке
```bash
cd ~/dsh-harness-fork
for p in ~/dsh-builder/patches/*.patch; do
  echo "=== $p ==="
  git apply --check "$p" && git apply "$p" && echo OK || echo FAILED
done
git add -A
git commit -m "android: apply dsh-builder patches"
git push
```

## 3. Переключить dsh-builder на форк
В `~/dsh-builder/.github/workflows/build-dsh.yml`:
- `repository: deepseek-ai/deepseek-harness` → `repository: x2v0/deepseek-harness`.
- Убрать шаги `Patch flock`, `Patch FiberState`, `Patch flock.c`.
- Оставить `Build system.node`, `Build require_builtin`.

## 4. Запустить сборку
```bash
cd ~/dsh-builder
git add .github/workflows/build-dsh.yml
git commit -m "ci: use x2v0/deepseek-harness fork"
git push
gh workflow run build-dsh.yml
gh run watch
```

## 5. Если упало
```bash
cd ~/dsh-builder
gh run view <RUN_ID> --log > ~/full.log
grep -n "Build require_builtin\|Build system.node\|Error" ~/full.log | head -40
sed -n '<НОМЕР>,<НОМЕР+80>p' ~/full.log
```

## 6. Если зелёное — скачать и запустить
```bash
gh run download -D ~/dsh-builder/download-vN
mkdir -p ~/dsh-finalN
tar -xzf ~/dsh-builder/download-vN/dsh-android-arm64/dsh-android-arm64.tar.gz -C ~/dsh-finalN
cd ~/dsh-finalN/dist-artifact
npm run start:web
```

## 7. Следующая задача — deepsick-адаптер
- `packages/llm/llm-deepsick/` в форке.
- Наследует `LlmAdapter` (`packages/llm/llm/src/index.ts`).
- `ctx.llm.registerAdapter(['deepsick'], adapter)`.
- Методы: `stream`, `listModels`, `resolveModel`, `prepareCall`.
- `baseURL` — через Config (`cordis.yml`).

## 8. Прочитать перед работой
- `GOALS.md`, `DSH.md`, `RESURRECT.md`.
