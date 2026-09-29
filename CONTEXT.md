# CONTEXT.md glossary

The Upper Arlington High School Computer Science Honor Society (CSHS) chapter website: a local admin console for chapter officers to manage content, and a static public site listing that content, eligibility rules, and the chapter roster.

## Roles & people

**Chapter**:
The Upper Arlington High School's local affiliate of the national CSTA Computer Science Honor Society. The entity this CMS represents; there is exactly one Chapter.
_Avoid_: club, organization

**CSHS**:
Computer Science Honor Society — the national CSTA program this Chapter belongs to. Spell out on first use in any document, then use the acronym.
_Avoid_: CS Honor Society, honor society (when a specific reference is meant)

**Advisor**:
The faculty member responsible for the Chapter; holds the `admin` role. This Chapter's advisor is Dr. Diane Kahle.
_Avoid_: sponsor, teacher-in-charge

**Admin**:
A CMS user role held by the Advisor and the student webmaster. Can do everything an Editor can, plus publish/unpublish content and manage user accounts (create, change role, deactivate).
_Avoid_: superadmin, owner

**Editor**:
A CMS user role held by Chapter officers. Can create, edit, and delete any Post or Page — including another Editor's drafts — but cannot publish/unpublish content or manage user accounts.
_Avoid_: contributor, author

## Content

**Post**:
A dated, feed-like content item — an announcement, meeting recap, or event write-up. Has a title, slug, Markdown body, draft/published status, author, and timestamps.
_Avoid_: article, announcement (when referring to the content type generally, not one specific item)

**Page**:
A static, evergreen content item that appears in the public site's navigation (e.g. About, Eligibility, Events, Roster, Join). Same fields and operations as a Post, minus the feed placement.
_Avoid_: static page

**Revision history** _(stretch goal)_:
A record of a Post or Page's prior saved versions, with the ability to roll back to one.

**Scheduled publishing** _(stretch goal)_:
Setting a future date/time at which a Draft automatically becomes Published, with no manual step at that time.

## Membership & eligibility

**Member**:
A student who has been inducted into the Chapter. Distinct from a Post/Page *author*, which may be any Editor or Admin regardless of Member status.
_Avoid_: officer (an officer is a Member with an additional Roster role — President or Volunteer)

**Induction**:
The event by which an accepted applicant becomes a Member.
_Avoid_: acceptance, enrollment

**Eligibility (entry requirement)**:
The threshold to *apply*: a 3.5+ GPA across 2 or more computer science courses, plus a completed application. Distinct from the Service hours requirement below, which is not required to join.
_Avoid_: qualifications, requirements (ambiguous with the completion requirement)

**Service hours (completion requirement)**:
20+ hours of CS-related community service a Member completes *while in the Chapter* — required to earn the Honor cord at graduation, not to join.
_Avoid_: volunteer hours, eligibility

**Honor cord**:
The light-blue cord awarded at graduation to Members who complete the Service hours requirement.
_Avoid_: sash, medal

## Roster

**Roster**:
The Page listing the Chapter's current officers: the President by name, and Volunteers.
_Avoid_: member list, directory

**President**:
The single named Member holding the Chapter's lead student officer position; the only individually-titled entry on the Roster.

**Volunteer**:
The Roster's label for any other officer or active Member listed there. A Volunteer is a Member who appears on the Roster; not every Member necessarily does.
_Avoid_: member (on the Roster specifically, "Volunteer" is the display label)
</content>
