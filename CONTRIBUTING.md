# Contributing

Thanks for helping make trading-skills better.

## Ground rules

1. **Zero dependencies.** Core and skill scripts use the Python standard library only (3.9+).
   Optional integrations may import a package lazily and fail with a clear message if it is missing.
2. **Numbers come from code.** Skills must never ask the model to estimate prices, indicators or sizes.
3. **Safety is not optional.** Anything that can place an order goes through `pre-trade-gate`
   approvals and the `order-router` preview -> confirm flow. Paper is the default.
4. **Offline tests.** Every feature ships with tests that run without network access (`tests/synth.py`).
5. **Market-neutral.** No market is the default or special. Use generic examples and let users configure.

## Layout

- `core/tradekit/` - the engine (source of truth)
- `skills/<name>/` - `SKILL.md` + `scripts/` (+ `references/`, `assets/`)
- `examples/` - strategies and watchlists (copied into skills as `assets/`)
- `tools/` - `sync_core.py`, `validate_skills.py`, `build_packages.py`
- `tests/` - unit + end-to-end CLI tests

## Workflow

```bash
# edit core/tradekit/... or skills/...
python3 tools/sync_core.py                 # vendor core + assets into every skill
python3 tools/validate_skills.py           # spec + conventions
python3 -m unittest discover -s tests -v   # offline tests
python3 tools/build_packages.py            # optional: dist/*.skill
```

Never edit `skills/*/scripts/_vendor/` by hand - CI fails if it drifts from `core/`.

## Adding a skill

- Folder name == `name` in frontmatter (lowercase, hyphens, <= 64 chars).
- `description`: what it does **and** "Use when ..." triggers, 50-1024 chars, no angle brackets.
- Keep `SKILL.md` focused (< ~500 lines); put detail in `references/`.
- Scripts: `argparse`, `--json` flag, markdown by default, one-line `ERROR:` on failure via `cli.run`.
- Add it to `.claude-plugin/marketplace.json` and the README table.

## Adding a broker

Implement `tradekit.brokers.base.Broker` (`account`, `positions`, `orders`, `place`, `cancel`), register it in
`brokers/__init__.py`, keep `live = True`, map order types explicitly, and add tests with a fake client
(see `TestKiteMapping`). Never log credentials; read them via `config.secret()`.

## Adding a data provider

Subclass `tradekit.data.Provider` (`bars`, optionally `quote`), return `Bars` with `meta["source"]` and
`meta["adjusted"]`, and register it in `get_provider`.

## Commit style

Conventional prefixes help the changelog: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`.
