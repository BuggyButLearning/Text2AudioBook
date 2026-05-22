# Enterprise Plan Audit Report

**Plan:** `.paul/phases/00-discovery-and-approval/00-02-PLAN.md`
**Audited:** 2026-05-21
**Auditor role:** Senior principal engineer + compliance reviewer
**Verdict:** Conditionally acceptable — approved after must-have + strongly-recommended upgrades applied (see §4).

---

## 1. Executive Verdict

The pre-audit plan was a sensible scoping of baseline characterization tests, but **would not have shipped clean under a real compliance review**. The single most serious finding: the project loads OpenAI API keys from `key.txt` as a documented fallback, and `key.txt` was **not in `.gitignore`**. A developer following PRD §FR-2 instructions could commit a live credential to a public repo on first push. That alone shifts the verdict from "ready" to "blocked".

After applying all must-have and strongly-recommended upgrades inline to the PLAN, the plan is **approved to proceed to APPLY**.

I would sign my name to the upgraded plan. I would not have signed the pre-audit version.

---

## 2. What Is Solid (Do Not Change)

- **Boundaries section.** Explicit lockout of all source files under modernization. No risk of scope creep into Phase 1+.
- **No new dependencies.** Plan correctly identifies that `pytest>=8.0.0` is already present and refuses to grow the dependency footprint mid-Phase-0.
- **Conda env discipline.** Pytest invocation uses the named env `text2audiobook` (`conda activate text2audiobook` or `conda run --name text2audiobook ...`) per CONDA_ENV_RULE.md — not a global interpreter or a base env.
- **Characterization framing.** The plan correctly tells the implementer to lock CURRENT behavior, not idealized future behavior. This is the right primitive for a regression net.
- **Traceability.** Every AC mapped to a specific test module. Every task `<done>` links back to an AC.
- **Parallelism.** Sidecar plan with `depends_on: []` does not block the 00-01 approval checkpoint. Sound dependency management.

Do not weaken any of these in subsequent revisions.

---

## 3. Enterprise Gaps Identified

Each item below was flagged as a non-obvious risk against an enterprise-grade test harness.

| # | Gap | Risk |
|---|-----|------|
| G1 | `.gitignore` does not list `key.txt`. PRD §FR-2 keeps `key.txt` as documented credential fallback. | **Foreseeable credential leak** — any commit + push by an inattentive contributor exposes a live OpenAI key. |
| G2 | Mock patch path under-specified. `tts_conversion.py` performs **deferred** `from openai import OpenAI` inside function bodies. Patching `tts_conversion.OpenAI` will not intercept calls — the test would silently make a real network request. | **Silent real-API call** in CI. Money + rate-limit + log-leak risk. |
| G3 | No verbatim pytest output captured. Plan asks for test/pass count only. | **Non-defensible audit evidence** — a future auditor cannot reconstruct what passed without re-running. |
| G4 | No pre-flight check that `pytest` is importable in the conda env. | If env not built, Task 2 fails opaquely. Plan offered no recovery path. |
| G5 | No `pytest.ini` / `pyproject.toml [tool.pytest.ini_options]`. `filterwarnings` defaults to "ignore". | Deprecation warnings from `openai`, `pydub`, `requests` will hide real signals. Markers can be silently typo'd. |
| G6 | No network-call guard at the socket layer. Plan relies on "we mocked it everywhere" — but a future test author could forget. | **Latent real-network call risk** in tests, especially as the suite grows in Phases 1–6. |
| G7 | Adversarial inputs not specified for `sanitize_output_filename`. Plan locks happy-path behavior only. | Path-traversal / null-byte / Windows-reserved-name behavior is uncharacterized; Phase 1 refactor may silently change behavior, no test catches it. |
| G8 | No suite wall-time budget. | Suite degrades into a slow drag; nobody runs it; regression net rots. |
| G9 | No abort/rollback on pytest collection error. Plan implicitly assumes Task 1 produces only valid Python. | Single syntax error blocks entire suite indefinitely. |
| G10 | `sys.path` mutation in conftest is fragile and will conflict with Phase 1+ packaging changes. | Documented limitation — flagged for Phase 1 to revisit; not blocking here. |

---

## 4. Upgrades Applied to Plan

All must-have and strongly-recommended findings have been applied **directly to `00-02-PLAN.md`**. The plan now contains audit-added content marked with `audit-added` references.

### Must-Have (Release-Blocking)

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| M1 | G1 — `.gitignore` missing `key.txt`; foreseeable credential leak | `files_modified`, AC-7 (new), Task 1 step 8, `tests/test_repo_hygiene.py` (new), verification, success_criteria | Plan now adds `key.txt`, `tmp/`, `*.mp3`, `*.wav` to `.gitignore` AND creates a `test_repo_hygiene.py` meta-test that fails if any required pattern is missing. Existing `.gitignore` entries are preserved (append-only). |
| M2 | G2 — wrong mock patch path on deferred openai import | AC-4 (strengthened) | Plan now mandates `monkeypatch.setattr("openai.OpenAI", FakeOpenAI)` (source module), not `"tts_conversion.OpenAI"`. Rationale documented inline for Phase 1 refactor. |
| M3 | G3 — non-defensible audit evidence | AC-6 (strengthened), Task 2 step 1, files_modified | Plan now writes verbatim pytest stdout + exit code to `.paul/phases/00-discovery-and-approval/00-02-pytest.log`. |
| M4 | G4 — no pre-flight check on conda env | New Task 0 | Plan now verifies `pytest` importable in `.conda` env BEFORE scaffolding. If missing, runs `conda env update --prune` once; if still missing, aborts and escalates. |

### Strongly Recommended

| # | Finding | Plan Section Modified | Change Applied |
|---|---------|----------------------|----------------|
| S1 | G5 — no strict pytest config | AC-8 (new), Task 1 step 7, files_modified | Plan now creates `pytest.ini` with `testpaths = tests`, `addopts = -ra --strict-markers --strict-config --tb=short`, `filterwarnings = error` (with documented narrow exceptions for upstream `pydub` / `openai` DeprecationWarnings), `pythonpath = .`, and declared markers. |
| S2 | G6 — no socket-level network block | AC-9 (new), Task 1 step 9 | Plan now installs an autouse fixture in `conftest.py` that monkeypatches `socket.socket.connect` to raise `RuntimeError` unless the test is marked `@pytest.mark.allow_network`. No new dep — stdlib only. |
| S3 | G7 — no adversarial inputs for `sanitize_output_filename` | AC-2 (strengthened) | Plan now requires characterization tests for null-byte injection, path traversal, Windows reserved names (`CON`/`NUL`/`AUX`/`PRN`/`COM1`/`LPT1`), very-long names (>1000 chars), empty string, whitespace-only string. Each test locks CURRENT behavior with a `# CHARACTERIZED — Phase 1 may harden this` comment. |
| S4 | G8 — no suite time budget | AC-6 (strengthened), Task 2 step 4 | Plan now asserts total wall-clock time < 5.0s and flags any single test > 1.0s via `--durations=10`. |
| S5 | G9 — no rollback on collection failure | Task 2 step 2 | Plan now defines explicit abort/rollback: identify offending file, delete it, log to SUMMARY, re-run once; second collection error → ABORT + HITL. |

### Deferred (Can Safely Defer)

| # | Finding | Rationale for Deferral |
|---|---------|----------------------|
| D1 | Add `pytest-cov` for baseline coverage measurement | New dependency. Coverage measurement belongs to Phase 7 (Testing, Validation, and Docs) per PRD §9. Deferring respects the boundary that no new deps land in Phase 0. |
| D2 | CI workflow integration (`.github/workflows/tests.yml`) | Phase 7 owns CI integration explicitly. Adding it in Phase 0 would either pre-empt a Phase 7 decision or introduce a half-built CI. |
| D3 | Refactor `sys.path` mutation in `conftest.py` → proper package install | The `sys.path` hack is fragile and will conflict with Phase 1+ packaging changes (G10). Flagged for Phase 1 to handle when it introduces the new settings/provider module structure. Not blocking the characterization tests today. |
| D4 | Pre-commit hook to enforce "no Claude attribution" global rule | Better enforced at git-hook layer than in pytest. Out of scope for a test-harness plan. |

---

## 5. Audit & Compliance Readiness

### Defensible audit evidence
- **Before:** Test count only in SUMMARY. Not reproducible without re-running.
- **After (M3):** Verbatim pytest stdout + exit code saved to `00-02-pytest.log`. SUMMARY references the log. An external auditor can reconstruct exactly which tests passed at this point in time.

### Silent failure prevention
- **Before:** `filterwarnings` default = "ignore"; mock-patch path could miss the deferred import; tests could quietly make real network calls.
- **After (S1, M2, S2):** Strict warnings, correct patch paths documented inline, autouse socket block. A test that accidentally calls OpenAI will raise loudly with `RuntimeError("Network access blocked in tests (audit S2)")`.

### Post-incident reconstruction
- **Before:** No characterization of adversarial inputs. If a Phase 1 refactor weakens `sanitize_output_filename` against path-traversal, no test catches it; no record of "what we considered safe in May 2026".
- **After (S3):** Adversarial inputs locked. Any behavior change in `sanitize_output_filename` (intended or not) trips a test, and the characterization comments tell the reviewer what was known at the time.

### Ownership / accountability
- **Before:** Implicit on whoever runs APPLY. Acceptable for solo project.
- **After:** Unchanged. Solo project; SUMMARY records the date and approver implicitly via STATE.md decision row.

### Credential hygiene
- **Before:** **FAIL.** `key.txt` not gitignored. Foreseeable credential leak.
- **After (M1):** **PASS.** `.gitignore` enforced. Meta-test (AC-7) ensures the protection is not silently removed in a future PR.

---

## 6. Final Release Bar

### What must be true before this plan ships
- All must-have upgrades applied to PLAN.md → **Done in this audit pass.**
- All strongly-recommended upgrades applied to PLAN.md → **Done in this audit pass.**
- APPLY phase produces:
  - All listed `tests/` files
  - `pytest.ini` at project root
  - Updated `.gitignore` (append-only)
  - Green pytest run (exit code 0)
  - `00-02-pytest.log` with verbatim output + EXIT line
  - SUMMARY.md with test counts, durations, any dropped tests, link to log

### Risks that remain if shipped as-is (post-audit)
- D3 (sys.path hack) is technical debt — flagged for Phase 1. Not blocking.
- D1 (pytest-cov) means we don't yet know coverage % of the locked behaviors. Phase 7 will surface this.
- Tkinter GUI logic remains untested. Phase 4 owns this; explicitly out of scope here.
- Real OpenAI/Ollama/HF behavior is mocked, not validated. Phase 7 smoke tests own this.

None of these are release-blocking for **a baseline regression net**, which is what this plan delivers.

### Would I sign my name to this system?
**Yes — post-upgrade.** No — pre-upgrade. The `.gitignore` finding alone (M1) would have failed a real review.

---

**Summary:** Applied **4 must-have + 5 strongly-recommended** upgrades to PLAN.md. Deferred **4 can-safely-defer** items (each with explicit reason routed to a later phase).
**Plan status:** Updated and ready for APPLY.

---
*Audit performed by PAUL Enterprise Audit Workflow*
*Audit template version: 1.0*
*Auditor stance: senior principal engineer + compliance reviewer, treating this as the last review before production.*
