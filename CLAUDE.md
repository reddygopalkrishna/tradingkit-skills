# Working on this repo

- Source of truth for shared code is `core/tradekit/`. Never edit `skills/*/scripts/_vendor/`.
- After changing `core/` or `examples/`, run `python3 tools/sync_core.py`.
- Before committing: `python3 tools/validate_skills.py` and `python3 -W ignore -m unittest discover -s tests`.
- Standard library only (Python 3.9+). Tests must run offline (use `tests/synth.py`).
- Keep the safety flow intact: pre-trade-gate approval -> order-router preview -> explicit confirm -> submit.
- Keep the pack market-neutral: no market or broker is special in docs or defaults.
