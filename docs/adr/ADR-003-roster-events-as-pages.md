# ADR-003: Roster and Events are Pages, not dedicated content types

**Status:** accepted
**Date:** 2026-09-29

## Context

A WordPress-style CMS would typically model a member roster and an events
calendar as their own structured content types (a roster entry with a photo
and role field; an event with a date, time, and location field). The rubric's
extra-credit list is fixed and closed — exactly ten named stretch goals,
capped at 5 points total — and neither a roster type nor an events type is on
it. Building either as real structured data would cost implementation time
without moving the grade, and Stage 1's deadline is tight.

## Decision

Roster and Events ship as ordinary Pages (About, Eligibility, Events, Roster,
Join) using the same Post/Page Markdown editor as everything else. No
`Officer` or `Event` database model exists. The Roster page's officer names,
and the Events page's meeting schedule, are edited as plain Markdown text
like any other Page content.

## Consequences

- Officers are added, removed, or reordered by hand-editing the Roster Page's
  body — there's no per-officer form, photo field, or validation.
- Event dates are prose in a Page, not queryable data — no calendar view,
  sorting, or "next meeting" widget is possible without a later model change.
- If the live chapter site later wants structured roster/events data, that's
  a new content type built on top of the existing Post/Page pattern, not a
  migration away from one.

## Why this is an ADR

It's a deliberate deviation from the obvious path — a CMS reader would expect
a roster and an events calendar to be modeled as data — and it's driven by a
constraint (the closed extra-credit list plus the deadline) that isn't
visible anywhere else in the code.
</content>
