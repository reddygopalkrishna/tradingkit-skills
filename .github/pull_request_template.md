## What

## Checklist
- [ ] Edited `core/tradekit` (not `_vendor`) and ran `python3 tools/sync_core.py`
- [ ] `python3 tools/validate_skills.py` passes
- [ ] `python3 -m unittest discover -s tests` passes (offline)
- [ ] New behaviour has tests
- [ ] Anything that can place orders still goes through pre-trade-gate + preview/confirm
