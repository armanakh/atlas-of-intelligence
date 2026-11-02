# Frontend Architecture Proposal

## Purpose and implementation basis

The frontend should make the curriculum easy to navigate and assess without enforcing a study sequence. It is a local-first knowledge explorer, not a course player or task manager. This proposal reflects the FastAPI routes and Pydantic schemas currently under `backend/app`; it does not assume additional endpoints.

The backend currently exposes one curriculum release candidate (v3.0.0) with 5 Tracks, 17 Phases and 334 Topics. Track membership and Phase placement are independent relationships. The imported data has 89 progress records and 245 Topics with no progress record. There are no imported curriculum resource, exercise or project items yet. Confidence is absent from current progress records.

## 1. Recommended information architecture

Use three primary areas: **Roadmap**, **Explore**, and **Progress**. A Topic is a contextual detail route, not another primary navigation destination.

- **Roadmap** gives a compact release overview, then exposes Tracks and Phases as separate ways to browse. Tracks can overlap and Phases do not define readiness or sequence. Display topic counts and, where useful, progress summaries derived from Topic IDs and the learner progress list.
- **Explore** is the searchable, filterable Topic index. Filters are Track, Phase and progress status. Show Track membership and Phase placement as distinct facets/tags. Link to Topic detail and show Related Topics from that detail view.
- **Topic view** explains a Topic and its relationships. Include description, objectives, membership/placement, prerequisite groups, readiness, Related Topics, downstream dependencies, and independent progress and confidence controls. Render optional resources, exercises or projects only when data actually exists.
- **Progress** summarizes the learner's recorded state. Show status counts, confidence distribution separately, Revisit Topics, and unassessed Topics. This is an overview for reflection, not a checklist or backlog.

“Unassessed” means that the progress endpoint returned no record for that Topic. An explicit `Not started` status is a different recorded assessment and must have its own label and visual treatment.

### Page and navigation structure

```text
App shell
├── Roadmap                 /roadmap
├── Explore                 /topics
│   └── Topic detail        /topics/:topicId
└── Progress                /progress

Release context             /settings/release (or a header dialog)
```

Keep the selected public `release_id` and learner context available throughout the app. Topic routes use stable Topic IDs and retain the current release and Explore filters in URL state where practical. The API does not provide a learner discovery/current-learner endpoint; learner context cannot yet be initialized automatically (see API gaps).

### Key user journeys

1. **Get oriented:** open the selected release, see its Track and Phase counts, choose either axis, then open a Topic.
2. **Find a concept:** search Topics, narrow by Track/Phase/status, open a result and follow its prerequisites or Related Topics.
3. **Understand readiness:** inspect each prerequisite group, with AND inside a group and OR between groups; see which members are Solid, unsatisfied, or unknown. Readiness is informational and never blocks exploration.
4. **Record an assessment:** change status or confidence independently. Clearing an assessment returns the Topic to unassessed; the UI should confirm the resulting empty state and should not describe evidence as history.
5. **Review progress:** compare status and confidence summaries, open Revisit or unassessed Topics, and return to Topic detail when useful.

## 2. Useful layout sketches

```text
┌──────────────────┬─────────────────────────────────────────────────┐
│ Roadmap           │ Release: v3.0.0   Learner: …   Search Topics     │
│ Explore           ├─────────────────────────────────────────────────┤
│ Progress          │ Curriculum overview                              │
│                   │ Tracks (membership view; may overlap)            │
│                   │ Phases (placement view)                          │
└──────────────────┴─────────────────────────────────────────────────┘
```

```text
┌────────────────────────────────┬─────────────────────────────────────┐
│ Topic title, ID, placement     │ Readiness: Ready / Not ready /      │
│ Purpose and description        │ Unknown (informational)             │
│ Learning objectives            │ Prerequisite groups                 │
│ Progress status control        │   group 1 AND members               │
│ Confidence control             │   OR                                │
│ Resources, if present           │   group 2 AND members               │
│                                │ Related Topics (separate section)   │
│                                │ Downstream dependencies             │
└────────────────────────────────┴─────────────────────────────────────┘
```

## 3. Component hierarchy

```text
App
├── AppShell
│   ├── PrimaryNavigation
│   ├── ReleaseSelector
│   ├── LearnerContext
│   └── RouteOutlet
├── RoadmapPage
│   ├── CurriculumSummary
│   ├── TrackBrowser / TrackCard
│   └── PhaseBrowser / PhaseRow
├── ExplorePage
│   ├── TopicFilters
│   ├── TopicSearch
│   └── TopicList / TopicRow
├── TopicPage
│   ├── TopicHeader / PlacementBadges
│   ├── ObjectiveList
│   ├── ProgressEditor
│   ├── ConfidenceEditor
│   ├── ReadinessPanel / PrerequisiteGroup
│   ├── RelatedTopicsPanel
│   ├── DownstreamPanel
│   └── OptionalLearningItems
└── ProgressPage
    ├── StatusSummary
    ├── ConfidenceSummary
    ├── RevisitList
    └── UnassessedList
```

Prefer reusable semantic components over a generic graph renderer. Prerequisite groups can be expressed clearly as grouped member lists with an explicit “OR” divider; Related Topics belong in a visibly separate section.

## 4. State management

- **Routing:** React Router. Encode the current route, stable Topic ID, selected release, and Explore filters in the URL when shareable within the local app. No server-side rendering is needed.
- **Server state:** TanStack Query for request caching, loading/error state, pagination and mutation invalidation. Query keys must include `release_id`, `learner_id`, filters and Topic ID as applicable.
- **Local UI state:** component state for dialogs, temporary form edits, expanded groups and view preferences. Avoid Redux; there is no broad client-side domain state that warrants it.
- **Derived state:** compute status counts, confidence summaries, unassessed Topics and locally searched results from paged Topic data and the progress list. Do not store derived readiness or infer a progress row when absent.
- **Mutations:** send only the edited field for status or confidence. On success, refresh the affected progress row/list and readiness query as needed. Use the API's DELETE operation to clear assessment; keep confirmation proportionate and do not imply evidence is deleted.

## 5. API integration plan

Create a small typed API client (for example, `apiFetch<T>()`) that reads the configured local API base URL, parses JSON, and normalizes the common `{error:{code,message,details}}` envelope. Use generated OpenAPI types if the backend publishes a stable OpenAPI document; otherwise maintain handwritten TypeScript types aligned with the Pydantic schemas and add contract checks during implementation.

| UI need | Existing API |
|---|---|
| Release list and current selection | `GET /api/v1/curriculum/releases`, `GET /api/v1/curriculum/active-release` |
| Explicit release selection | `PUT /api/v1/curriculum/active-release` with public UUID `release_id` |
| Release counts, Tracks, Phases and hierarchy | `GET /api/v1/curriculum/releases/{release_id}`, `/tracks`, `/phases`, `/hierarchy` |
| Topic list and facets | `GET /api/v1/curriculum/releases/{release_id}/topics` with `track_id`, `phase_id`, cursor and limit |
| Topic details | `GET /api/v1/curriculum/releases/{release_id}/topics/{topic_id}` |
| Prerequisites, Related Topics and downstream graph | `GET .../topics/{topic_id}/dependencies` |
| Learner readiness | `GET .../learners/{learner_id}/topics/{topic_id}/readiness` |
| Progress list and one Topic's progress | `GET .../learners/{learner_id}/progress`, `GET .../progress/{topic_id}` |
| Independent status/confidence updates and clearing | `PATCH .../progress/{topic_id}`, `DELETE .../progress/{topic_id}` |

Never expose or depend on internal integer release IDs. Treat the public UUID as release identity and the curriculum version as display metadata. Treat `learner_id` as opaque to frontend code even though its current representation is numeric. Keep reads explicitly scoped by release and learner. Do not call readiness for every Topic to create a dashboard; readiness is a per-Topic request and the UI can request it when a Topic is opened.

The Topic list endpoint is cursor-paginated (maximum page size 200). The current curriculum has 334 Topics, so the initial client can fetch pages and search locally across the loaded release. Topic status filtering can likewise use the progress list client-side. Do not assume one list page is complete.

## 6. Proposed project structure

```text
frontend/
├── index.html
├── package.json
├── vite.config.ts
└── src/
    ├── app/
    │   ├── App.tsx
    │   ├── router.tsx
    │   └── queryClient.ts
    ├── api/
    │   ├── client.ts
    │   ├── curriculum.ts
    │   ├── dependencies.ts
    │   ├── progress.ts
    │   └── types.ts
    ├── components/
    │   ├── layout/
    │   ├── topics/
    │   ├── relationships/
    │   └── progress/
    ├── features/
    │   ├── roadmap/
    │   ├── explore/
    │   ├── topic/
    │   └── progress/
    ├── hooks/
    ├── lib/
    ├── styles/
    └── main.tsx
```

Keep API request functions separate from view components. Feature components should depend on typed hooks/services rather than constructing URLs themselves. This leaves room for future authoring screens and release validation without mixing authoring operations into the learner-facing routes.

## 7. Visual design direction

- **Tone:** quiet, editorial and practical, with compact information and generous spacing around major sections. Use a warm near-white canvas (for example `#F6F5F1`), white or very light neutral cards, dark ink text, and muted slate for secondary labels.
- **Typography:** a legible sans-serif such as the system UI stack or Inter for body and headings. Use a restrained monospace style for stable Topic IDs and technical identifiers.
- **Navigation:** narrow persistent desktop rail; compact header for release and learner context. Keep breadcrumbs short and avoid multi-level menus.
- **Topic cards:** title and description first; small distinct labels for Track membership, Phase placement, and progress. Avoid implying that Track and Phase form one nested tree.
- **Progress:** readable labels plus restrained color. Use a neutral outlined “Unassessed” state and a separate explicit “Not started” status. Keep confidence on its own control and summary.
- **Relationships:** show prerequisite group members with AND grouping and OR separation. Use one consistent blue/teal family for prerequisites and a separate violet or neutral treatment for Related Topics. Link items by Topic ID/title. Avoid a force-directed graph as the default; a graph can obscure logic and is hard to scan.
- **Readiness:** use the exact `Ready`, `Not ready`, and `Unknown` outcomes with short explanatory text. Never style these as enabled/disabled actions.
- **Optional content:** if no resources or exercises are attached, use a quiet empty message such as “No learning items are attached yet.” Do not render empty panels as missing learner work.
- **States:** skeleton rows for initial loads; explicit retry for API errors; empty release state with a route to choose a release; empty search/filter results with clear-filters action; distinct unassessed and Not started states.

Use color alongside labels and icons so status and relationship types remain understandable without color perception. Keep motion minimal and respect reduced-motion settings.

## 8. Responsive behaviour

Design for desktop first, with a two-column shell and Topic detail layout. At tablet widths, reduce the navigation rail and collapse secondary metadata. On small screens, replace the rail with a menu or bottom navigation, stack Topic detail sections, and allow filter controls to open in a drawer. Keep prerequisite group labels visible when members wrap; avoid horizontal graph canvases. Ensure forms and hit targets remain usable by keyboard and touch.

## 9. API gaps and implementation constraints

1. **Learner discovery/current learner is absent.** All progress/readiness routes require `learner_id`, but there is no endpoint to list or resolve the local learner. The current database contains one unnamed learner, but the frontend must not assume or hard-code its integer ID. Before a polished frontend can load progress, add an explicit local learner resolution mechanism or supply the ID through a documented local configuration. This is the principal MVP blocker for a self-starting UI.
2. **Topic search is absent.** The list API supports Track and Phase filters, not text search or progress status. With 334 current Topics, fetching cursor pages and searching locally is suitable for the initial release. A server search endpoint is not required for this data size, but would matter as the curriculum grows.
3. **No bulk readiness endpoint.** Readiness is per Topic. Fetch it on Topic detail only; avoid N+1 dashboard calls. A future overview of readiness would require a deliberate API capability.
4. **Learning item bodies are not available.** Optional exercise/project/resource identifiers are preserved in curriculum metadata, but the current database has zero curriculum items and zero topic-item links, and there are no item detail routes. The Topic page should support a conditional section but cannot promise resource detail in the MVP.
5. **Release maturity report is not exposed by the browsing API.** The release summary surfaces status/version/schema/counts, not the full validation report or content-maturity qualifications. The current release is a candidate and learning items are absent. The UI should label the release status it receives and avoid implying complete authored content; richer validation disclosure would require a later API addition.
6. **History/evidence reading is not exposed.** Progress updates preserve history and evidence remains separate in the backend, but there are no endpoints to display either. They are not needed for the initial progress controls; do not present a history or evidence panel until read APIs are intentionally designed.

Other current API conventions are adequate for a read/explore MVP: release IDs are public UUIDs, curriculum reads are release-scoped, progress requests are learner-scoped, response schemas separate Topic relationships, and the common error envelope can support consistent UI errors.

## 10. Smallest useful MVP and sequence

The smallest useful frontend is: a release-aware app shell, Roadmap and Explore views, Topic detail with objectives and clearly separated relationships, per-Topic readiness, and independent status/confidence editing. Progress overview can follow once learner resolution is available. The UI should make the missing learner context explicit rather than silently choosing an ID.

Suggested sequence:

1. Confirm the local API base URL and resolve the learner discovery gap; bootstrap React, TypeScript, Vite, routing and query caching.
2. Build the shell, release list/active selector and explicit empty-active-release state.
3. Implement Roadmap and paginated Explore with Track/Phase facets and local search.
4. Implement Topic detail, prerequisite groups, separate Related Topics, downstream links and on-demand readiness.
5. Add progress read/edit/clear flows with independent status and confidence state and correct absent-record handling.
6. Add Progress overview from Topics plus progress records; include confidence empty state and unassessed count.
7. Finish responsive layouts, accessibility, loading/error/empty states and API contract verification.

No frontend code or backend/API changes are part of this proposal.
