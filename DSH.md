# DSH: ключевые правила из AGENTS.md

Источник: `deepseek-ai/deepseek-harness/AGENTS.md`

## Архитектура
- **All-plugin Cordis agent harness** — DSH строится на плагинах.
- Новое поведение — **extension points**, не изменение `agent-loop`.
- **Capability seam** = Service Definition / Service Provider / Consumer (три роли).

## API и версии
- Публичные API **pre-stable**. Любое изменение — обновить **всех потребителей**.
- Изменения persistence-типов — **аcknowledge** и **upgrade guide**.
- `SCHEMA_VERSION` — монотонный.

## Source vs Artifact
- **Source plane** = `src/`, **Artifact plane** = `lib/`.
- Гейты и тесты — только `src`. Патчи в `lib/` **не проверяются** гейтами.
- Патчить нужно `src/`, а не `lib/`.

## Плагины и конфиг
- **No hardcoded tunables** — deployment-varying choices = Config fields (`cordis.yml`), не хардкод.
- `cordis.yml` поддерживает `!!js` (JS-выражения) для plugin config.
- **Misconfiguration fails loud** — не пропускать молча.

## Типы и валидация
- **Trust TypeScript** на typed same-process boundaries.
- Runtime-валидация — только на границах: parser, config, queued, model/tool JSON, durable/file, worker, process, wire.
- **No `as unknown`** без причины.
- Opaque cross-boundary ids — **branded** (`Branded<B>`), не `string`.

## Model-visible ⟺ logged
- Всё, что попадает в запрос к модели, должно быть **восстановимо из session log**.
- Новый model-visible input → **session event**.

## Тесты и docs
- **`test:coverage`** — CI-гейт (per-file 100% на `packages/*/*/src`).
- Любое **non-trivial model/user-visible** изменение → **keyless recorded-session snapshot**.
- Изменения `agent-loop` / `session-lifecycle` / `SessionEventMap` → обновить **TypeScript и Python SDK** в одном PR.
- **Docs accompany every code change** (README + JSDoc).

## Upstream и PR
- Патчи — **минимальные, объяснимые**, в формате `git apply`.
- **Labels**: один `kind/*`, все `area/*`, native Issue Type.
- PR description — через `dsh-pr-description`.
- **Rebase** с `rerere.enabled`; `--force-with-lease`, не `--force`.

## Что это значит для нас
- `deepsick`-провайдер — **плагин** (Cordis), не патч `provider-data.generated.js`.
- `baseURL` — через **Config** (`cordis.yml`), не хардкод.
- `FiberState.ACTIVE → 2` — **workaround** (патч в `lib/`, не upstream-able). В upstream нужно иначе: `export const FiberState = {...} as const` в `src/`.
- `flock.c → fcntl()` — правильно (патч в `src/native/.../flock.c`), можно upstream как `#ifdef __ANDROID__`.
- `require_builtin` — upstream уже поддерживает Android (`__linux__ && __aarch64__`). Наш патч `build.ts` (whitelist) — минимальный, можно upstream.
