# Handoff: IPHS 400 MP2 CMS, extra credit, T16 scheduled publishing

**Written:** 2026-10-07, about 1:40am EDT
**Repo:** `C:\Rajan\E disk\My work\IPHS400\code\mp2-cms` → https://github.com/Rajan-Thakur/iphs400-mp2-cms
**Hard deadline:** the `mp2-final` tag is pushed and the email is sent by **2026-10-07 2:40pm EDT**. T16 counts only if its PR is merged *before* the tag. If time runs short, skip it; never let it put a submittable `main` at risk.

**Read first:** `docs/handoff/02_extra-credit_20261007.md`. It has the goal, the rubric rules for stretch goals, the ticket flow, the branch + PR steps, the original T16 design notes, the tests that must stay green, and the Windows environment quirks. This document covers only what changed since then and what the T15 session learned.

## State at handoff

- **T15 (revision history with rollback) is done:**
  - issue #16, labelled `stretch`, now closed
  - merged through PR #17 (merge commit `728bb14`)
  - the review findings comment is on #16
- **Local `main` = `origin/main` = `728bb14`.** **233 tests pass.** They were run on the branch at `1a513c0`, and the merge brought nothing else in.
- **Extra-credit tally so far:**
  - T15 revision history: 2 points, earned
  - T16 scheduled publishing: 1 point, still to do
  - "last two tickets done as branch + PR": 1 point, earned only if T16 also goes through its own branch + PR
- **The student's own uncommitted files:**
  - `notes/usage-ledger.csv` (modified)
  - `docs/transcripts/..._chat-session_06_...md` and `..._07_...md` (untracked)

  Leave them for the student. Stage only your own files.
- **`.claude/state/phase` says `T15`.** It was writable from the agent's Bash tool this session (`printf 'T16\n' > .claude/state/phase`). Set it to `T16` when the stage starts. If the student does it in PowerShell, tell them to use `Set-Content .claude\state\phase T16`. A bare `!` gives a parse error there, and PowerShell 5.1's `echo >` writes UTF-16, which the ledger hook can't read.

## Next session: T16, scheduled publishing

The flow is the same as T15. To see the format, look at issue #16's body and its review comment:
1. Create the issue, labelled `stretch`.
2. Agree the seams with the student, then write tests red-first.
3. Work on branch `t16-scheduled-publishing`.
4. Run the two-axis review.
5. Post the findings on the issue.
6. Commit `T16: … Closes #N`.
7. Push with `-u`, then `gh pr create`.
8. Ask the student before `gh pr merge --merge`.

### Decisions to raise with the student before writing tests

1. **Fix the glossary claim first.** `CONTEXT.md` says scheduled publishing makes a Draft become Published "automatically … with no manual step at that time". That's false for a static site: the item goes live on the next `cms publish` after its time. Reword it, and say so in the UI (and README, but README is the student's alone, so only suggest it).
2. **Don't add a `'scheduled'` status value.** `content.status` has `CHECK (status IN ('draft','published'))`, and SQLite can't change a CHECK without rebuilding the table. Use a nullable `publish_at` column on `content` instead.
   - A Scheduled item is a Draft with a `publish_at` set.
   - Export includes it once `publish_at <= now`. The alternative is for `cms publish` to flip it to Published first. Ask which the student prefers. Flipping keeps "only Published reaches `site/`" literally true, and makes the admin lists honest afterwards.
3. **Timezones.** Every stored time is UTC (`datetime('now')`), and the revision list shows a "UTC" suffix. An `<input type="datetime-local">` gives a naive local time. Decide whether to convert from the machine's local zone or label the input as UTC. Test the boundary with a fixed "now" (inject it); don't use the wall clock.
4. **Revisions.** Under T15's rule, publish and unpublish record no Revision. Setting or clearing a schedule is status-like, so by the same logic it should record none. Confirm with the student.
5. **Admin only.** Scheduling is a form of Publish, so it goes behind `require_admin`, the same as the publish and unpublish routes in `app/routes/content_crud.py`.

### How T15 left the schema-upgrade path (use it for `publish_at`)

- `app/db.py`: `connect()` calls `init_db(path)` once per database file per process (`_schema_ready`). `init_db` runs `SCHEMA + BACKFILL_REVISIONS` and closes its own connection in a `finally`.
- `CREATE TABLE IF NOT EXISTS` will **not** add a new column to an existing table. Add a Python step in `init_db` that checks `PRAGMA table_info(content)` and runs `ALTER TABLE content ADD COLUMN publish_at TEXT` only when the column is missing.
- Test it the way `tests/test_revisions.py::test_a_database_from_before_revisions_gets_a_starting_revision` does: a hand-written old schema (`PRE_T15_SCHEMA`), then monkeypatch `settings.DATABASE_PATH`. Note that a pre-T16 database already has a `revisions` table.
- `app/seed.py::_seed_content` inserts content directly, bypassing `create_content`, and runs `BACKFILL_REVISIONS` afterwards. A new nullable column needs no seed change.
- Also check the student's real `cms.db` by copying it to the scratchpad first; never open the real file during development. The T15 check: copy it, point `settings.DATABASE_PATH` at the copy, then read through `app.content`.

### Where it plugs in

- **Export:** `app/publish.py` reads `content_module.list_published` (home, posts) and `_exportable_pages` (nav, pages). Every "is this exportable?" rule must stay in one place.
- **Dashboard counts:** `app/content.py::count_by_status`. The lists and filters use `list_content` and `list_filtered`. A "Scheduled" badge needs a `.badge--scheduled` style next to `.badge--draft` in `app/style.css`.
- **Sweep and layout tests to extend:**
  - `tests/test_access_control_sweep.py`: add the new POST route to `POST_ROUTES_ADMIN_ONLY`.
  - `tests/test_admin_links.py`: `FAILED_POST_PAGES`.
  - `tests/test_phone_width.py`: `ADMIN_SCREENS`. Also give the `awkward_content` fixture a scheduled item if the list shows the badge.
- **The editor screen** (`templates/admin/content_form.html`) now has a Revisions section under the form. Put the schedule control in the form or as its own admin-only form, and keep it within 390px.

## Lessons from the T15 session

- **The two-axis review ran well** as two background `general-purpose` agents. To give them the diff, write it to the scratchpad *including untracked files*: `{ git diff main -- . ':!notes/usage-ledger.csv'; git diff --no-index /dev/null <new-file>; } > $SCRATCH/t16.diff`. Wait for both before fixing anything.
- **Found by review, not by tests:** a seed path that bypassed the new write path, and tests that picked an item via `list_content(...)[0]`, which ties on `created_at` at 1-second resolution. Look items up by slug.
- **When a test passes on its first run, prove it can fail.** Break the code temporarily and run it again, as done for the seed test.
- **Python heredocs inside Bash** turned `"\\n"` in replacement text into a real newline and broke a test file. Use the Edit tool for exact multi-line replacements.
- **`gh issue view N --comments` and `--json` can't be combined.** Use `--json comments -q '.comments[-1].body'`.
- **The student's terminal shares this working tree.** `git switch` changes their branch too, and a plain `git push` on a new branch fails with "no upstream". Tell them when you switch branches, and remind them they can use `git push origin main` from any branch.

## After T16, before 2:40pm (the student's own steps)

1. The student commits the ledger and the transcripts, and finishes report part (d).
2. Optional: `cms publish` + `cms deploy`, so the live Pages site shows T14's design and the new features. This needs the student's OK.
3. Run `PYTHONUTF8=1 uv run python scripts/check_submission.py --stage 2`. Then, from `main`: `git tag mp2-final && git push origin mp2-final`.
4. The student sends the email: subject `IPHS400 MP2 Stage 2 — Rajan Thakur`, with the repo URL, the Pages URL, the tag, and the report attached.

## Suggested skills

- `mattpocock-skills:grilling`: briefly, to settle the five T16 decisions above before writing the issue.
- `mattpocock-skills:tdd`: red-green at the seams the student agrees to.
- `mattpocock-skills:domain-modeling`: to reword the Scheduled publishing entry in `CONTEXT.md` and add the term "Scheduled" if it's used in the UI.
- `mattpocock-skills:code-review`: the two-axis review before the PR merges. This repo has no `docs/agents/issue-tracker.md`; use `gh` directly.
- `mattpocock-skills:handoff`: at the end of the session if work remains.
