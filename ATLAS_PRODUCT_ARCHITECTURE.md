# Atlas of Intelligence — Product Architecture

## Identity and philosophy

Atlas of Intelligence is a local-first personal intellectual knowledge atlas showing a learner's journey through mathematics, computation, engineering, machine learning and intelligence. Its central principle is: **The curriculum is the map. Personal progress is the journey drawn upon it.**

It is not an LMS, course player, task manager, tutor or completion dashboard. The source curriculum defines identities and relationships. Personal progress is a learner-owned overlay and never changes the map. Exploration remains open; readiness informs but never gates.

## Presentation architecture

| View concept | Authoritative source | Meaning |
|---|---|---|
| Territory | Track membership | Broad navigational lens. Five provisional identities; membership overlaps. |
| Field | Phase placement | Knowledge-area placement, independent of Territory. Phase order is retained but does not establish readiness. |
| Idea | Topic | Stable curriculum identity with title, description, objectives, affiliations and relationships. |
| Prerequisite | Prerequisite groups/members | Directed formal dependency; AND within each group, OR between groups. |
| Related connection | Related Topic link | Conceptual association; never affects readiness. |
| Journey mark | Learner progress/evidence | Personal assessment overlay, release-filtered for display. |

Territories and Fields are independent dimensions. A Topic has one canonical identity, one current Phase placement and one or more Track memberships. Never create a primary Track unless source data supplies one.

## Provisional Territories

These descriptions are editorial aids, not new curriculum definitions. Track descriptions and the CS/Engineering boundary are undocumented; author approval is required.

| Territory | Provisional description | Evidence/caveat |
|---|---|---|
| Computer Science | Programming, software design, data structures and algorithms as general computational practice. | TR-CS, mainly PH01/PH03. No source rationale for its boundary with Engineering. |
| Mathematics | Formal and quantitative ideas for describing, deriving and reasoning about systems. | TR-MATH also appears in applied Fields. |
| Engineering & Systems | Numerical implementation, inference and operational concerns around ML systems. | TR-ENG cluster includes PH06/13/14/16; definition is editorial. |
| Machine Learning | Learning methods, models, neural systems and applied ML techniques. | TR-ML is broad and overlaps other Tracks. |
| Intelligence & Advanced AI | Ideas and systems concerned with intelligence and advanced AI. | TR-AI; does not imply every Topic is research or an exclusive destination. |

Source membership counts overlap: CS 34, Mathematics 111, Engineering 90, ML 200, AI 48. 128 Topics have multiple Track affiliations. No Topic has both CS and Engineering membership, though prerequisites cross the boundary. Preserve both and show actual links.

## Navigation and journeys

Primary navigation: **Atlas**, **Territories**, **Fields**, **Ideas**, **Journey**. Idea detail and Connections are contextual views, not disconnected product areas. Global context keeps the selected release and local learner visible.

- **Orient:** select release, scan Territories and ordered Fields, then enter any field or area.
- **Explore:** choose a Territory lens or Field placement; open a unique Idea, retaining all its affiliations.
- **Find:** search by stable Topic ID/title and filter by Territory, Field or exact progress state.
- **Follow:** inspect prerequisite groups/readiness, downstream dependents, or the separate Related list.
- **Reflect:** see learner marks over the same map; revisit a Topic or explore unassessed territory.

## Vocabulary

Use Atlas, Territory, Field, Idea, Connections, Release and Journey consistently. Pair presentation wording with source labels where useful, e.g. “Field · PH06”. Use exact learner states: Solid, Learning, Practicing, Revisit, Not started and Unassessed. “Unexplored” must not stand in for an absent record; Solid is not permanent mastery.

## State and technical boundaries

- Curriculum source: release-scoped API data.
- Presentation metadata: editorial Territory descriptions, icon/pattern and display order in separately versioned frontend configuration until authoring is approved; never alter the registry or invent a primary affiliation.
- Derived data: counts/intersections/layout from fully paginated release data.
- Learner data: progress/confidence from learner-scoped API; no implicit records or automatic transfer between retired/split Topics.
- Local state: selected release UUID, view, filters, focus, expansion and zoom; URL-encode navigational state when useful.

Keep React/TypeScript/Vite, React Router, the current typed API client and Atlas context. Use stable Topic IDs in routes and public release UUIDs in queries. No new API endpoint is required for the first redesign; use the existing release, hierarchy, paginated Topic, detail, dependency/readiness and progress contracts. No graph dependency is justified for the overview.

## Decisions for human review

Approve the Territory descriptions, especially CS versus Engineering; decide if editorial presentation metadata should later be authored per release. Initial prototypes can label descriptions provisional while preserving source identities.
