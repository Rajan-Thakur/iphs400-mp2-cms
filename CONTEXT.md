# CONTEXT.md glossary

A small, WordPress-style web CMS: a local admin console where Editors and Admins manage content, and a static public site that publishes it. The content model is intentionally generic — built with no specific client in mind. A specific client site has been built *using* this CMS. The site was created for the Upper Arlington High School's Computer Science Honor Society chapter (UAHS CSHS), specifically for Dr. Diane Kahle (faculty advisor). The chapter needs a website to promote computer science among UAHS students.

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
A static, evergreen content item — same fields and operations as a Post, plus appearing in the public site's navigation once published. The UAHS-CSHS website includes The Latest Posts, Coursework, Contact Us, About Us (mission + why join + eligibility + requirements + questions).
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
The `site/` directory `cms publish` generates from currently-published content only; what `cms deploy` pushes to GitHub Pages. Every link in it is relative. A link written in a body from the site root (`/contact-us.html`) is rewritten relative to the file it lands in (`./contact-us.html`, or `../contact-us.html` from a Post), since GitHub Pages serves the site from a subfolder. The admin preview keeps it as written.

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

## Media

**Media library**:
The admin screen where Editors and Admins upload images for Posts (PNG or JPEG, 2 MB or less) and copy each one's Snippet. The files live in `media/`, which is git-ignored like the database; `cms publish` copies all of `media/` into the Static export.
_Avoid_: gallery, uploads

**Alt text**:
The words that describe an image to someone who can't see it; a screen reader reads them aloud. Every upload needs it, and the Snippet carries it into the Post's `<img alt>`.
_Avoid_: caption (a caption is shown to everyone)

**Snippet**:
The Markdown the Media library shows for each image, `![<Alt text>](media/<file>)`, ready to paste into a Post's body. `media/` is read from the site root, so the Static export rewrites it relative to the file it lands in (`../media/<file>` from a Post), and the editor's preview does the same for its own page.

## Search

**Search index**:
The file `search-index.json` that `cms publish` writes into the Static export: the title, relative URL, and Excerpt of every Published Post and Page, and nothing from a Draft. The public site's search page (`search.html`) reads it in the reader's browser and lists every item whose title or Excerpt holds each typed word. There is no search server.
_Avoid_: search database

**Excerpt**:
The start of a Post's or Page's body as plain text, 160 characters or fewer, cut at a word and ended with "…" when there is more. Search results show it under the title.
_Avoid_: summary, snippet (a Snippet is the Media library's Markdown)
