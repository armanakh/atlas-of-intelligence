# Atlas of Intelligence — Implementation Plan

## Guardrails

Preserve the curriculum, DB schema/data, stable IDs and existing API contracts. Presentation mappings stay in versioned frontend configuration until authoring semantics are agreed. Derived layout is not persisted. Learner data is never inferred or transferred.

## Stage 0 — Typed model and Survey prototype

**Objective:** Validate how independent Territory and Field axes can intersect without duplicating Ideas.

**Scope:** Pure TypeScript view model and prototype using actual release data; no persistent writes.

**Likely files:** frontend/src/features/atlas/atlasModel.ts, territories.ts, Survey components.

**Dependencies:** This blueprint.

**Acceptance:** All 5 provisional Territories and 17 ordered Fields represented; counts derive from source memberships; multi-affiliated Topic stays one identity; no implied dependency lines.

**Tests/verification:** Unit tests for intersection/count calculations and pagination; typecheck/build; desktop/mobile keyboard/screenshot review.

## Stage 1 — Shared shell and design tokens

**Objective:** Make all routes feel like one Atlas.

**Scope:** Global type/color/spacing tokens, shared navigation, release and learner context, responsive/focus states.

**Likely files:** AppShell.tsx, route config, styles.css, shared Territory/Field/state marks.

**Dependencies:** Stage 0 tokens and terminology.

**Acceptance:** Territory accents do not masquerade as progress state; all views have consistent context; mobile nav and accessible focus work.

**Tests/verification:** Build/typecheck, route smoke, contrast and keyboard review, screenshots.

## Stage 2 — Atlas Survey overview

**Objective:** Put the curriculum structure at the center of the product.

**Scope:** Territory lenses, ordered Field spine, intersection summaries, progressive disclosure.

**Likely files:** frontend/src/features/atlas/AtlasPage.tsx, SurveyCanvas.tsx, Atlas view model/data hooks.

**Dependencies:** Stages 0–1; existing release and hierarchy endpoints.

**Acceptance:** Totals only after all Topic pages load; 334 Ideas are not equal dots; source ordering is labeled placement not readiness; no fabricated edges.

**Tests/verification:** Actual-release count comparison; pagination/loading tests; no-active-release state; responsive visual review.

## Stage 3 — Territory, Field and Ideas browsing

**Objective:** Support navigation from either independent curriculum axis.

**Scope:** Territory lens, Field view, Ideas index/search/filter, URL-preserved selection.

**Likely files:** features/territory, features/field, features/ideas, shared Idea row.

**Dependencies:** Stage 2.

**Acceptance:** Membership filters show multi-affiliated Topics once with all affiliations; Field remains a single placement; back/forward restores filter context.

**Tests/verification:** Search/filter tests, multi-membership fixture, URL tests and measured performance.

## Stage 4 — Idea detail and focused Connections

**Objective:** Explain why an Idea exists and how it connects.

**Scope:** Objectives, separate state controls, grouped prerequisite/readiness view, Related section, downstream navigation, optional materials.

**Likely files:** Idea detail, prerequisite groups, connection panel, shared progress editor.

**Dependencies:** Stages 1–3 and existing dependency API.

**Acceptance:** AND/OR is exact; unknown is distinct; only Solid satisfies; Related never participates; exploration stays open.

**Tests/verification:** Synthetic status matrix plus real examples (CAL-004/NN-007, CS-006/ENG-004); keyboard equivalent; API contract smoke.

## Stage 5 — Journey overlay

**Objective:** Put current learner marks on the map without making a task dashboard.

**Scope:** Dynamic state filters/counts, Revisit list, unassessed count, separate confidence summary.

**Likely files:** Journey view, state legend/marks, derived view model and progress query.

**Dependencies:** Stages 2–4 and learner/progress API.

**Acceptance:** Counts reconcile dynamically; missing records remain absent; confidence/readiness independent; learner resolution failure does not hide map.

**Tests/verification:** Fixtures for absent/Not started/confidence-only; current DB read-only count check; GET has no mutation.

## Stage 6 — Accessibility, polish and release review

**Objective:** Verify coherence and usability across the complete application.

**Scope:** Motion, responsive layout, loading/error states, documentation and performance.

**Likely files:** Shared components/styles/tests/docs.

**Dependencies:** Stages 1–5.

**Acceptance:** AA contrast, no color-only meaning, reduced motion, 200% zoom, no phone-width overflow, no arbitrary graph, source/proposal distinction clear.

**Tests/verification:** Full applicable suites, production build, accessibility and real-release review, screenshots of overview, Territory, Field, Idea, Connections and Journey.

## Dependency order

Stage 0 → Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5 → Stage 6.

## Recommended first implementation task

Implement **Stage 0 only**: a pure, typed Atlas view model and non-persisted Survey prototype backed by actual paginated release data. This tests the central architecture risk—independent Tracks and Phases without false nesting or duplicate Topic identities—before replacing current pages. Do not start with a full graph renderer or isolated Progress redesign.
