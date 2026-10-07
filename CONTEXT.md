# CONTEXT.md glossary

A small, WordPress-style web CMS: a local admin console where Editors and Admins manage content, and a static public site that publishes it. The content model is intentionally generic — built with no specific client in mind. A specific client site will be built *using* this CMS later. The CMS will be built for the Upper Arlington High School's Computer Science Honor Society chapter (UAHS CSHS), specifically for Dr. Diane Kahle (faculty advisor). The chapter needs a website to promote computer science among UAHS students.

## Roles

**Admin**:
A CMS user role with full permissions: everything an Editor can do, plus publishing/unpublishing content and managing user accounts (create, change role, deactivate). When this CMS is introduced to the client for the UAHS CSHS chapter, Dr. Kahle will be given admin permissions.
_Avoid_: superadmin, owner

**Editor**:
A CMS user role that can create, edit, and delete any Post or Page — including another user's drafts — but cannot publish/unpublish content or manage user accounts. Student officers will be given Editor permissions.
_Avoid_: contributor, author (an Author is a content attribute, not a role)

## Content

**Post**:
A dated, feed-like content item with a title, slug, Markdown body, draft/published status, author, and timestamps. Appears in the site's chronological feed.
_Avoid_: article, entry

**Page**:
A static, evergreen content item — same fields and operations as a Post, plus appearing in the public site's navigation once published. Client-specific website will include Latest Posts, offered computer science coursework, contact us, about us (mission + why join + eligibility + requirements + awards).
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

**Revision**:
One saved version of a Post or Page: its title, slug, and body, who saved it, and when, numbered 1, 2, 3… within that item. Every create, edit, and Roll back records one; Publish and unpublish do not, since they change Status, not content.
_Avoid_: snapshot, history entry

**Revision history**:
The list of an item's Revisions, newest first, on its edit screen. The newest is the Current one.

**Roll back** (verb):
Returning an item's title, slug, and body to those of an earlier Revision. Editors and Admins can do it; it is itself recorded as a new Revision, so a Roll back can be undone the same way. Status is unchanged: a Published item's restored text reaches the site on the next static export.
_Avoid_: restore, revert, undo

**Scheduled publishing**:
An Admin setting a future time, in UTC, after which a Draft becomes Published. The public site is static, so nothing happens at that moment: the item becomes Published on the next `cms publish` after its time, which switches it before writing the static export. Setting or cancelling a schedule records no Revision, since it changes Status, not content.
_Avoid_: auto-publish, publishing "automatically"

**Scheduled**:
A Draft with a publish time set. The dashboard and lists show it as "scheduled", apart from other Drafts. Publishing or unpublishing it by hand cancels its schedule.
