# CONTEXT.md glossary

A small, WordPress-style web CMS: a local admin console where Editors and Admins manage content, and a static public site that publishes it. The content model is intentionally generic — built with no specific client in mind. (A specific client site will be built *using* this CMS as a later, separate project.)

## Roles

**Admin**:
A CMS user role with full permissions: everything an Editor can do, plus publishing/unpublishing content and managing user accounts (create, change role, deactivate).
_Avoid_: superadmin, owner

**Editor**:
A CMS user role that can create, edit, and delete any Post or Page — including another user's drafts — but cannot publish/unpublish content or manage user accounts.
_Avoid_: contributor, author (an Author is a content attribute, not a role)

## Content

**Post**:
A dated, feed-like content item with a title, slug, Markdown body, draft/published status, author, and timestamps. Appears in the site's chronological feed.
_Avoid_: article, entry

**Page**:
A static, evergreen content item — same fields and operations as a Post, plus appearing in the public site's navigation once published.
_Avoid_: static page (redundant)

**Slug**:
The URL-safe identifier for a Post or Page, unique within its kind, used to build its published path.

**Status (Draft / Published)**:
The two states a Post or Page can be in. A Draft is visible only in the admin console; only a Published item reaches the static export.
_Avoid_: live/unlive, active/inactive

**Author**:
The user (Admin or Editor) recorded as having written a given Post or Page. Distinct from whoever most recently edited it.

## Publishing

**Publish** (verb):
The admin-only action that flips a content item's status from Draft to Published, making it eligible to appear in the next static export.
_Avoid_: approve (there's no separate approval workflow — publish is a single, direct action)

**Static export**:
The `site/` directory `cms publish` generates from currently-published content only; what `cms deploy` pushes to GitHub Pages.

**Revision history** _(stretch goal)_:
A record of a Post or Page's prior saved versions, with the ability to roll back to one.

**Scheduled publishing** _(stretch goal)_:
Setting a future date/time at which a Draft automatically becomes Published, with no manual step at that time.
