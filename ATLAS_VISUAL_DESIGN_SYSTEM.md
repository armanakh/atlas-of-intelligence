# Atlas of Intelligence — Visual Design System

## Semantic dimensions

Keep four visual channels independent: Territory identity (Track affiliation), Field identity (Phase placement), learning state (learner record), and relationship type (prerequisite or Related). Status markers must not resemble Territory marks. Fields do not use readiness color. Color is always paired with text, shape or line style.

## Color tokens

### Canvas and text

| Token | Value | Role |
|---|---|---|
| paper-0 | #F7F4EC | Main canvas |
| paper-1 | #EEE9DD | Raised/selected surface |
| paper-2 | #E2DACB | Quiet separator/hover |
| ink-0 | #172A31 | Main text |
| ink-1 | #344A50 | Supporting text |
| ink-inverse | #F8F5EC | Text on dark surface |
| atlas-night | #142C38 | Survey/relationship canvas |
| line | #C8C2B5 | Dividers |
| focus | #0A63CE | Keyboard focus outline |

### Learning state

| Token | Value | Non-color cue |
|---|---|---|
| state-solid | #187A4B | Filled circle + check + “Solid” |
| state-learning | #146FA8 | Open circle/arc + “Learning” |
| state-practicing | #A85A00 | Square + “Practicing” |
| state-revisit | #B33F4B | Diamond/return mark + “Revisit” |
| state-not-started | #626B73 | Neutral solid square + “Not started” |
| state-unassessed | #9AA3AA | Hollow circle + “Unassessed” |

Not started is an explicit record; Unassessed means no record. Never render both as the same unlabeled gray mark.

### Territory accents

Editorial accents are used only on narrow borders, small labeled marks and patterns, not as large fills that could be mistaken for status:

| Territory | Accent | Pattern cue |
|---|---|---|
| Computer Science | #4A68B8 | Parallel strokes |
| Mathematics | #72539A | Point/grid |
| Engineering & Systems | #08786F | Right-angle/circuit |
| Machine Learning | #9B477B | Layered bands |
| Intelligence & Advanced AI | #A15A28 | Open rings |

These values are proposed tokens, not source data, and should be reviewed alongside the Territory descriptions. Always show the Territory name.

### Connections

Prerequisite = directional solid arrow, explicit label, AND members grouped and OR alternatives separated. Downstream = arrow away from the selected Idea, labeled “uses this as a prerequisite.” Related Topic = thin dashed neutral link in a separate panel/layer. Focused paths emphasize only the selected relationship set.

## Typography

Use local fonts only: display serif Georgia / Iowan Old Style / Palatino fallback; UI sans Inter if bundled, otherwise system sans; IDs in ui-monospace. Do not fetch fonts remotely.

| Role | Size / line-height |
|---|---|
| Atlas heading | clamp(40px, 4.6vw, 72px) / 1.0 |
| Territory/Field heading | 29px / 1.15 |
| Idea title | clamp(32px, 3.4vw, 54px) / 1.05 |
| Section heading | 22px / 1.25 |
| Body | 16px / 1.55 |
| Supporting prose | 14px / 1.5 |
| Navigation/labels | 13px / 1.35 |
| ID/meta | 12px / 1.35 |

Meaningful text must not fall below 12px. Uppercase eyebrows are secondary only.

## Spacing and composition

4px base scale: 4, 8, 12, 16, 24, 32, 48, 64, 88. Desktop max width 1440px; navigation rail 248px; gutters clamp(20px, 4vw, 64px). Use a 12-column editorial grid on desktop, 6 on tablet, one on narrow screens. Prefer open surfaces, typographic grouping and rules over card stacks.

## Component rules

- Survey canvas: structured Field bands and Territory intersection labels; never a force-directed 334-node cloud.
- Territory mark: accent + pattern + name; all memberships shown.
- Field band: source phase ID/title/order, count and intersecting Territories.
- Idea row: one stable ID/title, one Field placement and all Territory affiliations.
- State mark: token, shape/icon and exact label.
- Prerequisite panel: grouped AND/OR logic, ready/not_ready/unknown with unknown distinct.
- Related panel: separate from formal dependency.
- Journey overlay: exact states and count/link affordances; no completion rings, streaks, deadlines or invented trends.
- Empty/loading/error states: distinguish genuinely zero from unavailable or still paging.

## Interaction and accessibility

Hover gets a subtle surface tint without layout shift. Keyboard focus uses a 3px outline with 2px offset. Selected lenses have persistent label/outline and accessible selected/current semantics. Filters display release, active filters, count and reset. Relationship focus is keyboard operable; Escape/back restores context. Motion uses 120–220ms opacity/transform, with reduced-motion support; no parallax or node rearrangement.

Target WCAG 2.2 AA contrast. Use minimum 44×44px touch targets, tab order, skip link, screen-reader summaries for intersections and group logic, zoom to 200%, and text equivalents for SVG connections. On mobile, use a list/map index rather than requiring panning.
