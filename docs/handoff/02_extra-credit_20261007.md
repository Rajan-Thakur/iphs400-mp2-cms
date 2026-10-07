# Handoff: IPHS 400 MP2 CMS, extra credit (stretch goals)

**Written:** 2026-10-07, about 1:00am EDT
**Repo:** `C:\Rajan\E disk\My work\IPHS400\code\mp2-cms` → https://github.com/Rajan-Thakur/iphs400-mp2-cms
**Hard deadline:** `mp2-final` tag pushed and email sent by **2026-10-07 2:40pm EDT** (end of grace). Extra credit only counts if it is merged *before* the tag is created.

## Goal of this session

Earn up to 4 extra-credit points (rubric `docs/mp2-grading-rubric_20260922.md` §5) with the two stretch goals the spec already planned. Spec issue #1, "Out of Scope" and "Further Notes", says they come later as `stretch` issues.

1. **Revision history with rollback** (2 pts)
2. **Scheduled publishing** (1 pt)
3. **"Last two tickets done as branch + pull request"** (1 pt): build 1 and 2 on their own branches and merge each through a PR, so they are the last two tickets.

The rubric rule for each stretch goal: its own issue labelled **`stretch`** (the label exists), passing tests, and a `/code-review` findings comment posted on the issue **before it closes**. MP2 is Pass/No-Pass at 70, so extra credit can't change the outcome. **Never let it put a submittable `main` at risk.**

## State at handoff

- `main` is at `b2539ee` (T14) and pushed. T01–T14 = issues #2–#15, all closed; spec #1 stays open on purpose.
- **Tests:** 221 pass (`uv run pytest`). The Playwright browser tests run here because Chromium is installed.
- **Rubric walkthrough:** a fresh-clone run of C1–C7, D1, D2, D4, F1, F2 and F4 passed 42/42 before T14.
- **Checker:** `check_submission.py --stage 2` passes 21/22; only `mp2-final` is missing.
- **The student's own uncommitted items:** the report, handoff 01, the session 05 transcript, and the usage ledger. Advice already given:
  - commit these *before* starting extra credit, so `main` is submittable at any moment;
  - do **not** commit the raw `docs/transcripts/*.jsonl`, which breaks the H2 naming pattern.
- The live Pages site may still show the pre-T14 design. The student was told how to run `cms publish` / `cms deploy` themselves.

## How work is done in this repo (follow exactly)

- Read `CLAUDE.md`, `CONTEXT.md` and `docs/adr/` first. `CLAUDE.md` holds the hard rules: relative paths only, CSRF on every state-changing form, sanitized Markdown, only published content reaches `site/`, ask before adding a dependency.
- **Ticket flow, as done for T10–T14** (see any of issues #11–#15 for the issue body format and the review-comment format):
  1. Create the issue first, labelled `stretch`. Use the body sections Parent / What to build / Acceptance criteria / Blocked by.
  2. TDD at agreed seams: red first, and confirm the seams with the student before writing tests (`mattpocock-skills:tdd`).
  3. Two-axis `/code-review`: two parallel background sub-agents, one Standards and one Spec. Wait for both, then fix in one batch.
  4. Post the findings and how each was resolved as a comment on the issue, **before** merging.
  5. Merge through a PR whose body or merge commit says `Closes #N`. The commit/PR title should start with the ticket id. The next ids are T15 and T16, since CLAUDE.md wants the `T0N:` style.
- **Branch + PR:** `git switch -c t15-revision-history` → commit → `git push -u origin <branch>` → `gh pr create` → merge (`gh pr merge --merge`) only once tests and the review comment are done. **Never force-push.** Never commit straight to `main` for these two.
- Stage files explicitly; never `git add -A`. `README.md` is the student's alone. Never commit `.env`, `*.db` or `grading_prompt.md` (it is excluded via `.git/info/exclude`).

## Design notes for the two features (decide details with the student)

- **Schema change needs a migration.** `app/db.py` creates tables with `CREATE TABLE IF NOT EXISTS`, so new tables are fine. A new *column* on `content` (e.g. `publish_at`) needs an `ALTER TABLE … ADD COLUMN` path, or existing `cms.db` files, including the student's, won't have it. Test both a fresh database and an existing one.
- **Where the code lives:**
  - Content CRUD is one factory for Posts and Pages (`app/routes/content_crud.py` → `build_content_router`).
  - Data access is in `app/content.py` (every write is kind-scoped).
  - Export is in `app/publish.py` (`render_site`, `_exportable_pages`, `content_module.list_published`).
  - Templates are in `templates/admin/` and `templates/public/`; styling is in `app/style.css`.
- **Revision history:**
  - Snapshot title, slug and body on every save, plus who and when.
  - The editor lists revisions, and rollback restores one; rollback itself should be recorded as a new revision.
  - Open question for the student: may Editors roll back, or only Admins? Editors can already edit and delete.
  - Rollback is a state-changing POST, so it needs CSRF. Add it to the access-control sweep (`tests/test_access_control_sweep.py`) and to the CSRF replay coverage.
- **Scheduled publishing:**
  - An Admin sets a future publish time.
  - "Only published content reaches `site/`" must still hold: a scheduled item stays out of the export until its time has passed.
  - Because the site is static, it goes live on the next `cms publish` after that time. Say so in the UI or README rather than implying it is automatic.
  - Show "Scheduled" distinctly on the dashboard and in the lists (badge styles live in `app/style.css`).
- **Keep these green:**
  - `tests/test_phone_width.py`: every new screen must fit 390px; add the new screens to `ADMIN_SCREENS`.
  - `tests/test_admin_links.py`: every link must resolve.
  - `tests/test_access_denied.py`.
  - `tests/test_no_secrets.py`.

## Before 2:40pm, in order

1. Both PRs merged, or abandoned if time is short (skip, don't rush).
2. The student commits their remaining docs and finishes report part (d).
3. Run `PYTHONUTF8=1 uv run python scripts/check_submission.py --stage 2`, then `git tag mp2-final && git push origin mp2-final` from `main`.
4. The student emails `IPHS400 MP2 Stage 2 — Rajan Thakur` with the repo URL, Pages URL and tag, and the report attached.

## Environment quirks (Windows)

- A user-level and machine-level `PYTHONPATH` points at Python 3.12's `site-packages`, which contains an old `argparse.py` backport. That breaks `cms` with `TypeError: … unexpected keyword argument 'required'` and breaks pytest. **Always run `export PYTHONPATH=` (Bash) or `$env:PYTHONPATH=""` (PowerShell) before `uv run`.**
- uv lives at `C:\Users\rajan\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe` and is not on PATH in Bash. gh lives at `C:\Program Files\GitHub CLI\gh.exe`.
- Run `check_submission.py` with `PYTHONUTF8=1`.
- `.claude/state/phase` became unwritable from the agent's tools on 2026-10-07 (it is stuck at `T13`). Ask the student to set it, e.g. `echo T15 > .claude/state/phase`.
- Demo logins in the student's local `cms.db` still use the `.env.example` placeholder passwords. Their `.env` has different values; a reset one-liner was offered and not yet run.
- For screenshots and visual checks, a scratchpad Playwright pattern works: a uvicorn thread on a bound socket plus a database seeded like `scripts/seed_demo.py`. See the `live_server` fixture in `tests/conftest.py`.

## Suggested skills

- `mattpocock-skills:tdd`: red-green at agreed seams for each feature.
- `mattpocock-skills:code-review`: the two-axis review before each merge (required by CLAUDE.md and the rubric).
- `mattpocock-skills:implement`: if driving each stretch ticket end to end.
- `mattpocock-skills:domain-modeling`: if "revision" or "scheduled" enter the vocabulary. Add them to `CONTEXT.md` rather than inventing synonyms.
