# Atlas of Intelligence — Experience Specification

## Global shell

Persistent shell identifies Atlas, active release and local learner context. Primary nav: Atlas, Territories, Fields, Ideas, Journey. Search is globally available but not the dominant entry. Use public release UUIDs and opaque learner IDs in API scope; never expose release database keys. Release selection remains explicit.

## Atlas overview: the Survey

The overview answers: what intellectual territories exist, what Fields intersect them, and where can I enter?

Use an editorial survey with the 17 Phase Fields in original order and five Territory lenses across the top. Territory selection highlights/filter memberships; it does not own a Field. Each Field shows its Topic count and labeled Territory intersections. Do not render 334 equal dots. Expanding a Field reveals its Idea list and affiliations. An Idea with multiple memberships remains one canonical item with multiple labeled affiliations. Phase order is labeled as source order/placement, never a readiness or completion sequence.

Illustrative layout:

    Release v3.0.0 · Phase order is placement, not a gate          [Search]
    Territory lenses: CS | Mathematics | Engineering | ML | Intelligence
    PH00 Computational and Mathematical Foundations · 8 · Mathematics
    PH01 Programming and Software Design · 22 · Computer Science
    ...
    PH06 Numerical Computing and Autodiff · 39 · Engineering, Math, ML
    ...
    PH16 Advanced Intelligence and Research · 24 · AI, ML, Engineering
    Selected Field · Territory intersections · Ideas

Do not show complete totals until all paginated Topic results are loaded.

## Territory exploration

A Territory is a lens over its source Track membership. Show the provisional editorial description, Fields containing member Topics, counts and selected Ideas. Preserve every affiliation; no “primary” marker. No current Idea belongs to both CS and Engineering, but prerequisite edges connect them; show actual dependencies rather than merging their views.

## Field exploration

Show Phase ID, source title, ordinal, Topic count and its Territory intersections. Render one Idea list and all affiliations. A Field is a placement, not a nested child in a Territory tree. Provide filtering by Territory without changing the Topic's source associations.

## Ideas index

Search by stable ID/title/description. Filters: Territory, Field, exact learner state and release. Preserve filters in URL. Rows show ID, title, one Field placement, all Track-derived Territory labels and exact learner state or Unassessed. Search locates Ideas; Atlas browse remains the primary experience. Page/virtualize only when measured performance warrants it.

## Idea detail

1. Stable ID, title, description and maturity qualification where relevant.
2. All Territory affiliations and the one Phase placement as separately labeled facts.
3. Learning target, objectives and available depth/revisit guidance.
4. Progress and confidence controls, independently editable.
5. Prerequisite groups with AND within each, OR alternatives, and readiness. Only Solid satisfies. Unknown differs from unsatisfied. No groups means no formal prerequisites.
6. Direct downstream dependencies, with optional transitive exploration.
7. Related Topics in their own section.
8. Exercises, projects and resources only if actual linked curriculum items exist.

Keep reading content primary; relationship detail progressively disclosed. Readiness never limits navigation. Learner evidence is not curriculum resource content.

## Connections

Default is a compact grouped list. Optional focused SVG shows only the selected Idea and a bounded set of its actual edges:

    Selected Idea
    Prerequisite route A (AND): Idea 1 + Idea 2
                    OR
    Prerequisite route B (AND): Idea 3
    Related (not prerequisites): Idea 4 · Idea 5
    Downstream: Ideas that name this as prerequisite

Use directional arrows for prerequisite/downstream and dashed neutral links for Related. Never let Related links reach readiness. Expand ancestors/downstream on request; avoid full-graph default.

Use source examples in explanatory onboarding: linear algebra to linear models (LA-001/LA-002 → ML-007), calculus to backpropagation (CAL-004/CAL-007 → NN-007), programming/data structures to engineering implementation (CS-006 → ENG-004), and ML to advanced intelligence (ML topics → AI-010/011/012).

## Journey

Journey is a learner-state overlay on the same Atlas. Derive counts dynamically from selected release Topics and current learner progress. Show Solid, Learning, Practicing, Revisit, Not started and Unassessed exactly. Missing row is Unassessed; Not started is an explicit row. Confidence is a separate coordinate and may be present without progress status. Readiness is separate; Solid alone satisfies prerequisite edges.

Suggested view: map with a state filter, a concise Learning/Practicing strip, Revisit return links, and unassessed count plus browse action rather than a giant list. Confidence distribution appears separately only when values exist. No fabricated milestones, trends, completion percentage, recommendations, deadlines or streaks. Do not hardcode current counts.

## States and routes

- No active release: explain and offer explicit release selection.
- Loading/paging: show loading; withhold total aggregates until complete.
- Learner missing/ambiguous: curriculum still browsable; personal overlay explains unavailable state and never creates/selects a learner.
- Missing progress: explicit Unassessed, never prefilled Not started.
- Empty prerequisite/Related list: state absence clearly.
- API error: keep context and allow retry; do not replace with false zeros.

Canonical routes retain stable Topic IDs. Return links preserve Territory/Field/filter context. Breadcrumbs use “via” for navigation path (e.g. Atlas → via Mathematics → PH04 → LA-001), not a false hierarchy. The public release ID is part of query state, not an internal integer.

## API sufficiency

Current release/list/selection, hierarchy, paginated Topic, Track, Phase, detail, dependency/readiness, learner and progress endpoints suffice. Derive intersection counts client-side after all pages load. No API gap is required for the initial design. Consider an aggregate read endpoint only after measuring that local derivation is too slow.
