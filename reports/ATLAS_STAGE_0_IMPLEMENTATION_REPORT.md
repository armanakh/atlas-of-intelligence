# Atlas Stage 0: Typed View Model and Survey Prototype

## Result

The `/roadmap` route now presents a read-only Atlas Survey using the selected curriculum release. It is derived from the paginated curriculum API, with no hardcoded curriculum totals or Topic identities. The prototype keeps Track membership (Territories) separate from Phase placement (Fields), and shows every Idea once with its stable Topic ID and all Track affiliations.

Territory descriptions are explicitly marked as provisional editorial copy. Field order follows the Phase order returned by the release hierarchy. The Survey adds no relationship lines and does not infer relationships from visual position.

## Visual redesign

The Survey now uses a route-scoped deep navy canvas, bold sans-serif hierarchy, bright cyan Field structure, and distinct saturated Territory colors: coral, blue, orange, yellow, and green. Idea rows show Territory affiliations as named tags. Actual learner progress appears as a separate filled status badge; absent status records display as **Unassessed** and are never created by the Survey. Other routes retain the existing global style.

## Architecture decisions

- `atlasModel.ts` is a pure TypeScript transformation: it builds canonical Idea objects once, then shares those objects in Field membership and filters.
- Cursor collection lives in the API layer, so the API client has no dependency on the Atlas presentation feature.
- A repeated Topic ID, unknown Track reference, repeated page cursor, incomplete source, or failed request prevents the UI from presenting complete aggregates.
- Territory counts and per-Field intersections are computed from each Topic's Track memberships. Phase placement is read only from `phase_id`.
- No Territory is selected as primary. Topics with no valid Phase remain in the unplaced set rather than being assigned to a Field.
- The existing `/roadmap` route hosts the prototype; global navigation and the other pages remain outside this milestone.
- The Survey performs reads only. It does not call progress mutation operations or persist presentation mappings.

## Live release reconciliation

Observed from the active v3.0.0 release through the local API after all cursor pages had loaded:

| Measure | Derived | Reconciliation |
| --- | ---: | --- |
| Territories / source Tracks | 5 | 5 |
| Fields / source Phases | 17 | 17 |
| Unique Ideas / Topics | 334 | 334 unique stable IDs |
| Field placements | 334 | Field counts sum to 334 |
| Ideas without a valid Field | 0 | 0 |
| Track affiliations | 483 | Territory counts sum to 483; overlaps are expected |

Territory membership counts:

| Territory (source Track) | Ideas |
| --- | ---: |
| Intelligence & Advanced AI | 48 |
| Computer Science | 34 |
| Engineering & Systems | 90 |
| Mathematics | 111 |
| Machine Learning | 200 |

Field Idea counts in API Phase order:

| Field | Count | Field | Count | Field | Count |
| --- | ---: | --- | ---: | --- | ---: |
| PH00 | 8 | PH06 | 39 | PH12 | 14 |
| PH01 | 22 | PH07 | 23 | PH13 | 26 |
| PH02 | 10 | PH08 | 13 | PH14 | 19 |
| PH03 | 12 | PH09 | 31 | PH15 | 24 |
| PH04 | 21 | PH10 | 20 | PH16 | 24 |
| PH05 | 15 | PH11 | 13 | | |

All Field counts total 334. Multi-Track topics appear once in each Field and once in each matching Territory count; they are never duplicated as Ideas.

## Verification

- `pnpm test:atlas`: 8 tests passed.
- `pnpm build`: TypeScript compilation and Vite production build passed.
- Browser QA against the local API: 17 Field bands rendered; aggregate counts matched the API-derived Topic memberships; expanding PH06 showed its three Territory intersections; selecting `AD-001` retained its identity and exposed Engineering & Systems, Mathematics, and Machine Learning affiliations.
- Responsive QA at 390 × 844: all 17 Fields remained present with no horizontal page overflow; named affiliation tags wrap beneath Idea titles.
- No API load error state appeared during the live review.

## Files created or changed

- `frontend/src/features/atlas/atlasModel.ts` — view-model types, pure derivation, filtering, and loading-state handling.
- `frontend/src/api/pagination.ts` — generic cursor-page collector with repeated-cursor protection.
- `frontend/src/features/atlas/AtlasSurveyPage.tsx` — Survey UI, Territory selection, Field expansion, Idea inspection and read-only progress badges.
- `frontend/src/api/client.ts` — exhausts cursor pagination before returning `allTopics`.
- `frontend/src/app/AtlasContext.tsx` — exposes data-loading errors and progress-query availability for the Survey state.
- `frontend/src/app/AppShell.tsx` — activates route-scoped Atlas chrome styling on `/roadmap`.
- `frontend/src/app/App.tsx` — renders the Survey on the existing `/roadmap` route.
- `frontend/src/styles.css` — scoped Survey styles and responsive layout.
- `frontend/tests/atlasModel.test.ts` — focused model and pagination tests.
- `frontend/package.json` — `test:atlas` script.
- `frontend/review/atlas-survey-desktop.jpg` and `frontend/review/atlas-survey-mobile.jpg` — fresh redesign review captures.

## Problems and next step

The public navigation still calls this route “Roadmap”; this is retained for Stage 0 to avoid global navigation redesign. Territory names are the source Track titles, while their explanatory descriptions remain provisional editorial metadata. Neither is stored in the curriculum or database.

The independent Territory and Field dimensions reconcile cleanly against this release. The next useful step is product review of the Survey and provisional editorial labels before expanding the experience beyond Stage 0.
