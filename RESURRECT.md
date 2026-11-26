# RESURRECT.md — холодный старт

## Что строим
DSH (DeepSeek Harness) на Android **полностью из GitHub Actions**. Артефакт: скачал → распаковал → запустил.
Затем — бесплатный доступ к DeepSeek через `deepsick`-провайдер (WebView-мост).

## Где что лежит
- `~/dsh-harness-fork/` — **наш форк** `x2v0/deepseek-harness` (source of truth для патчей).
- `~/dsh-builder/` — репозиторий `x2v0/dsh-builder` (YAML + `scripts/` + `patches/` + `GOALS.md` + `DSH.md`).
- `~/dsh-final*/dist-artifact/` — распакованные артефакты из GH Actions.
- `~/dsh-workspace/` — рабочая папка DSH (`memory_bank.md`, `logs/`).

## Правила
- #0 Python heredoc; #1 `cd` первой строкой; #2 бэкап `.bak`; #3 не отступать; #4 не ломать; #5 `wta` где можно; #11 без regex (построчно); #555 Termux (`/tmp` может быть недоступен — писать в `~/`).
- DSH: всё — плагин; `src/` vs `lib/`; `baseURL` — через Config; `listModels` — для GUI; failure codes — из `LLM_FAILURE_CODES`.
- **Никаких бинарных prebuild**: всё собирается на GitHub Actions.

## Что сделано
1. **Форк** `x2v0/deepseek-harness` создан, `upstream/master` подтянут.
2. **`dsh-builder`**: YAML + `scripts/` + `patches/` + `GOALS.md` + `DSH.md`.
3. **Изучены контракты DSH**: `packages/llm/llm/src/index.ts` (`LlmRuntime`, `LlmAdapter`), `types.ts` (`StreamChunk`, `GenerateOptions`, `LlmFailure`, `LlmConfigurableProvider`), `AGENTS.md`, `architecture.md`, `development.md`, `cordis-primer.md`.

## Что осталось
### 1. Применить патчи в форке
- В `~/dsh-harness-fork` применить `~/dsh-builder/patches/*.patch` через `git apply`.
- Закоммитить: `git add -A && git commit -m "android: apply dsh-builder patches" && git push`.

### 2. Переключить `dsh-builder` на форк
- В `build-dsh.yml`: `repository: deepseek-ai/deepseek-harness` → `repository: x2v0/deepseek-harness`.
- Убрать шаги `Patch flock`, `Patch FiberState`, `Patch flock.c` (они уже в форке).
- Оставить `Build system.node`, `Build require_builtin`.

### 3. `deepsick`-адаптер (цель 3)
- `packages/llm/llm-deepsick/` — новый пакет в форке.
- Наследует `LlmAdapter`, регистрируется `ctx.llm.registerAdapter(['deepsick'], adapter)`.
- Реализует: `stream`, `listModels`, `resolveModel`, `prepareCall`.
- `baseURL` — через Config (`cordis.yml`).
- `StreamChunk`: `block-start` → `text-delta` → `block-end` → `usage` → `finish`.
- `LlmError` с кодами из `LLM_FAILURE_CODES`.

## Известные блокеры
- `Build require_builtin` падал на устаревших анкорах `platform.cc` (upstream уже поддерживает Android). Скрипт переписан: без `patch_file` для `platform.cc`, только `patch_build_ts`.
- `tar` на Android не поддерживает hard links — в YAML `tar --hard-dereference`.
- `pnpm install` может падать на `workspace:`, если вызывается `npm` вместо `pnpm`.

## Команды для старта
```bash
cd ~/dsh-builder
git pull
gh workflow run build-dsh.yml
gh run watch
```

## Ссылки
- Форк: https://github.com/x2v0/deepseek-harness
- Builder: https://github.com/x2v0/dsh-builder
- Upstream: https://github.com/deepseek-ai/deepseek-harness
