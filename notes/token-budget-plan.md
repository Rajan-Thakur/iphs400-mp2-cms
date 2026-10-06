# Token budget plan

(Part 5.4 of the manual. Filled in before the first `/implement` commit.)

## Model/effort mapping

What's actually available on this account is the Claude 5 family (Sonnet 5,
Opus 5.5, Fable 5.1) and Haiku 4.5 — no `opusplan` split needed since Sonnet 5
at `high`/`xhigh` effort has covered the planning stages so far. Adjusted
from the manual's default:

| Stage | Model | Effort | Estimate (% of a 5-hour window) |
|---|---|---|---|
| `/research`, quick lookups | Sonnet 5 | low | ~2% |
| `/grill-with-docs`, `/to-spec`, `/to-tickets` | Sonnet 5 | medium | ~20% (already spent — see `notes/usage-ledger.csv`) |
| `/implement` + `/tdd` (per ticket) | Sonnet 5 | xhigh | ~8% each |
| `/code-review` (per ticket) | Opus 5.5 | high | ~3% each |

## Estimate

9 tickets × (8% + 3%) ≈ 99% of a 5-hour window for implement+review alone,
plus the ~20% already spent on grill/spec/tickets ⇒ roughly **1.2 five-hour
windows** total, call it 6 hours of active work. Against a weekly cap that's
a small slice — the weekly budget is not the binding constraint here.

**The real constraint is the wall-clock deadline, not the token budget**:
Stage 2 is due today (Oct 6) with grace to Oct 7, 2:40pm. That's the number
that actually matters this week, not the 5-hour-window percentage.

## What gets cut first if this estimate is wrong

In order:
1. **The two extra-credit stretch goals** (revision history with rollback,
   scheduled publishing) — dropped first and without hesitation. Extra
   credit only counts if the base score is already ≥70, so it's pure
   downside to protect at the expense of core points.
2. **T09's sweep ticket scope** — narrowed to the highest-point D-series
   gaps (CSRF, access-control tests) over lower-value polish if time is
   short.
3. **F3/F4 UX polish** (mobile width, label clarity) on later tickets —
   kept on the tickets that are cheap to add it to (T01's shared layout),
   dropped on any ticket where it would need a second pass.
4. Only as a last resort: a core ticket itself (e.g. T08's admin console),
   accepting the direct C5 point loss rather than missing the deadline
   entirely.
</content>
