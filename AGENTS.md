# AgriTwin Pakistan — Coding Agent Rules

These rules are extracted from Section 0 of `docs/IMPLEMENTATION_PLAN.md` (the project's single source of truth).

1. **Work phase by phase, in order** (Phase 0 → Phase 8). Do not start Phase N+1 until every item in Phase N's *Definition of Done* is ticked and the human has confirmed.
2. **Use Planning mode / produce a short plan before each phase**, then implement. Keep commits small. One branch per phase (`phase-1-pipeline`), merge to `main` at the end, tag `phase-N`.
3. **Tick checkboxes in this file as you go** (`- [x]`) and add a one-line note beside anything you deviate on. Log every decision in `docs/DECISIONS.md` and every change in `CHANGELOG.md`.
4. **Never fabricate data, metrics, citations, or results.** Every number that appears in the dashboard, README, or report must be produced by code actually run on real data. Anything simulated must be stored with `source='simulated'` and shown with a visible "SIMULATED" badge in the UI.
5. **Never commit secrets** (API keys, GEE service-account JSON, DB URLs, device keys). Use `.env` (git-ignored) and ship `.env.example`.
6. **When you hit a 🧑 HUMAN task, stop that thread.** Tell the user precisely what to do (copy-paste steps), then continue with everything that does *not* depend on it, using fixtures/mocks.
7. **Write the tests as you write the code, run them, and report results truthfully** (including failures). No "should work" claims without running.
8. **Keep code explainable.** Two students must defend this project. Prefer clear, boring code over clever code. Docstring every public function; add a short `README.md` in each major package explaining *what* and *why*.
9. **Train/serve parity:** feature engineering used for training and for live inference must be the *same code* (`agritwin/features`). No copy-pasted logic.
10. **Reproducibility:** pin dependency versions, fix random seeds, save data/version hashes with every trained model.
11. **Do not add paid services** or unlisted heavy dependencies. Free tiers only.
12. If a requirement is ambiguous, take the default in Section 2, record it in `DECISIONS.md`, and continue.

**Legend:** 🧑 = human-only task · 🤖 = agent task · `MUST` = stated in a project document · `SHOULD` = strongly recommended · `COULD` = stretch · ⚠️ = risk/caveat.
