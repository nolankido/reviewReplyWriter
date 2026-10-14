# Keyboard handoffs in the owner reply workflow

Selecting a library draft rebuilt its buttons and could remove the focused
selection without a new focus destination. Some explicit recovery paths also
focused disabled editors before busy controls were restored. The new small local
focus helper queues the intended destination and flushes after controls and their
normal safety gates are re-enabled.

| Explicit action | Focus destination |
| --- | --- |
| Open library/inbox draft, generate/regenerate, open a recovered generation | Saved review and owner-policy summary, opened for reading |
| Review routed to personal handling | Manual-handling heading |
| Check an uncertain generation | Its result message |
| Check a saved change | Saved-version comparison heading |
| Keep editor text after saved-state reconciliation | Reply editor, after busy controls are restored |
| Recover a working copy | Matching reply editor, inspection-only orphan text, or compose review input |
| Acknowledged edit/decision | Check findings or approved status |
| Unhandled action error | Visible error notice |

Source-first reading avoids focusing a text input just to announce a newly opened
reply. Explicit recovery of editable text intentionally focuses its editing field.
The helper opens a relevant details panel when requested and scrolls only as
needed with automatic, not smooth, movement. Headings/status destinations use
`tabindex=-1`, remain outside the ordinary Tab sequence, and have visible focus
outlines. The source summary retains native summary/keyboard behavior. Existing
live status regions remain declared; their actual assistive-technology behavior
has not been independently tested here.

Cancelled replacement guards run before any handoff is queued. They preserve the
current work and make no request to move focus. Ordinary/background renders do
not queue source focus, so refreshing saved data does not deliberately pull focus
from the editor. A later error handoff replaces a queued earlier destination.
Missing, disconnected, disabled and hidden targets are not focused. There are no
new global shortcuts, focus traps, automatic text selection or checkbox changes.
Focus does not authorize policy, save content, approve, copy or post a reply.

## Executed checks and limits

Node executes the real focus helper and actual library/render/run code in a
controlled DOM. It covers deferred enabled-editor focus, removed library buttons,
opened source context, cancelled guards, retained editor text, background renders,
error notice focus and invalid/hidden targets. These are controlled state checks,
not browser rendering or operator feedback. Python checks target uniqueness,
native summary/tab semantics, non-authorizing helper behavior and local asset
serving with existing security headers. The complete Python regression suite and
real Python launcher/recovered-backup HTTP workflows remain executed.

Chromium scenarios now use keyboard Enter for saved-library selection, dismiss a
replacement guard, and check source, comparison, result-message and editor focus.
They are prepared but unexecuted in this workspace. Actual desktop/mobile browser
navigation, virtual-keyboard behavior, focus visibility and screen-reader
announcements still need real target devices. This is a bounded owner-workflow
repair, not accessibility conformance or best-in-class certification.
