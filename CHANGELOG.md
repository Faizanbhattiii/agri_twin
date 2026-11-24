# Changelog

All notable changes to the AgriTwin Pakistan project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to Semantic Versioning.

---

## [0.1.0] - 2026-11-24

### Phase 0: Project Scaffolding, Tooling & Verification Harness
- Completed Phase 0–8 master plan specifications in `docs/IMPLEMENTATION_PLAN.md`.
- Established Agent rules in `AGENTS.md` and `.agents/rules/agritwin.md` adhering to Section 0.
- Logged key decisions D1–D19 in `docs/DECISIONS.md`.
- Set up repository structure (`agritwin/`, `config/`, `data/`, `firmware/`, `simulator/`, `frontend/`, `tests/`, `docs/`).
- Added pinned dependencies in `requirements.txt` and `pyproject.toml`.
- Added `.env.example` with non-secret defaults.
- Authored crop configuration in `config/crops/wheat.yaml` with GDD thresholds, crop coefficients $K_c$, critical stages, and conversion factors.
- Implemented core settings loader in `agritwin/core/config.py`.
- Implemented and passed configuration test suite (`tests/test_config.py`).
