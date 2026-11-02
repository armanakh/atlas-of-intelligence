# Backend REST API Contract Proposal

**Status:** Approved API contract, implemented in the backend for Task 4B.

## 1. Existing implementation inspected

- SQLAlchemy models are in `backend/app/db/models.py`. Curriculum rows are release snapshots. Topic identity is durable across releases. Topic Track membership, Phase placement, prerequisite groups/members, and Related Topics use separate tables. Learner progress is keyed by learner and stable Topic ID, independent of release. Progress history and evidence are separate records.
- `backend/app/schemas/curriculum.py` contains import-boundary Pydantic models only. It allows unknown curriculum input metadata, and `LearnerProgressInput` is an import schema, not an API PATCH schema.
- `backend/app/importer.py` validates and imports ZIP packages atomically through a CLI. It is not an HTTP service. It stores the package status on the release and records imported learner snapshots in progress history.
- `backend/app/dependency.py` exposes `DependencyEngine(session, release_id=..., learner_id=...)`, `evaluate_readiness`, `direct_prerequisites`, `direct_dependents`, `prerequisite_ancestors`, `downstream_dependents`, and `related_topics`. It returns `ready`, `not_ready`, or `unknown`; Related Topics are separate.
- `backend/app/db/database.py` provides `make_engine` and `make_session_factory`; SQLite foreign keys are enabled and the session factory has `autoflush=False`. `backend/app/db/initialize.py` upgrades through Alembic. No FastAPI app, route modules, API response schemas, or application service layer exists yet.
- Tests cover database/model/import/dependency behavior. No API contract or HTTP behavior is currently tested.

The local database after the Task 4B migration contains curriculum `3.0.0`, curriculum schema `1.0.0-draft`, status `curriculum_release_candidate`, public release UUID `bf1acf06-8b70-4e07-bd6e-c422c7742ec3`, and one unnamed learner. The active-release pointer is empty; the candidate remains unselected.

## 2. Contract conventions

- Base path: `/api/v1`.
- Use stable Topic IDs in topic routes. Scope every curriculum read by a public `release_id`; scope every learner read or write by a `learner_id`.
- Do not return SQLAlchemy objects or table/column names. Return explicit Pydantic response models. Put unrecognized optional curriculum fields in a `metadata: dict[str, Any]` field so extension data survives without making database structure part of the public contract.
- `release_id` in the HTTP contract is a public immutable UUID, not the database integer primary key. It must be generated once when a release is created, stored uniquely and non-null, and returned by the API. The service resolves it internally; clients never receive the ORM key.
- Collection responses use `{ "items": [...], "next_cursor": null }`. Initial dataset sizes are small, but cursor pagination avoids making list endpoints unbounded as authoring grows. Filters are optional and explicit.
- No read endpoint creates a progress record. Missing progress is represented as `null` for a single Topic or omitted from the list of assessed records; explicit `Not started` is returned as a real record.

## 3. Proposed endpoints

### Curriculum overview

| Method and path | Purpose |
|---|---|
| `GET /api/v1/curriculum/releases` | List release summaries, including public UUID `release_id`, curriculum version, curriculum schema version, package status, and imported timestamp. |
| `GET /api/v1/curriculum/active-release` | Retrieve the release selected by the explicit singleton pointer. Return `409 active_release_not_selected` if no pointer is set. |
| `PUT /api/v1/curriculum/active-release` | Explicitly select a release after validation. Replaces the previous pointer transactionally; does not infer or alter release status. |
| `GET /api/v1/curriculum/releases/{release_id}` | Release metadata and counts useful to the client. |
| `GET /api/v1/curriculum/releases/{release_id}/tracks` | List Tracks. |
| `GET /api/v1/curriculum/releases/{release_id}/phases` | List Phases. |
| `GET /api/v1/curriculum/releases/{release_id}/topics?track_id=&phase_id=&cursor=&limit=` | List Topic summaries filtered by membership and/or placement. A Topic can appear in multiple Track-filtered results. |
| `GET /api/v1/curriculum/releases/{release_id}/hierarchy` | Return overview references grouped by Tracks and Phases. Tracks and Phases remain separate axes; do not nest Phases under Tracks or infer a relationship between them. |

Selection request/response:

```http
PUT /api/v1/curriculum/active-release
Content-Type: application/json

{"release_id": "f20aed51-bc34-41b5-96c8-39c48edffcb2"}
```

The request returns `200` with the selected `ReleaseSummary`. The release must exist and pass the release validation gate. The imported `curriculum_release_candidate` row is not selected automatically; setup explicitly sends its returned public UUID after validation. Selecting a release does not promote or otherwise rewrite its free-text status.

### Topic exploration and relationships

| Method and path | Purpose |
|---|---|
| `GET /api/v1/curriculum/releases/{release_id}/topics/{topic_id}` | Topic detail, objectives, recognized descriptive fields, extensible metadata, Track IDs, and Phase ID. |
| `GET /api/v1/curriculum/releases/{release_id}/topics/{topic_id}/dependencies` | Direct prerequisite groups, direct dependents, transitive ancestors, transitive downstream dependents, and a separate Related Topics field. |

The hierarchy response should contain light references rather than repeating complete Topic details. Topic detail can inline objectives because each Topic has a small objective list; no separate objective endpoint is needed initially.

### Dependency evaluation

| Method and path | Purpose |
|---|---|
| `GET /api/v1/curriculum/releases/{release_id}/learners/{learner_id}/topics/{topic_id}/readiness` | Read-only readiness for that explicit release, learner, and Topic. |

The handler resolves the public `release_id` UUID to the internal release row, validates the learner, then calls the existing `DependencyEngine`. It must serialize the engine result without recomputing prerequisite semantics. Phase placement and Related Topics must not be folded into this response as readiness conditions.

### Learner progress

### Local learner resolution

| Method and path | Purpose |
|---|---|
| `GET /api/v1/learners/current` | Return the existing local learner when exactly one exists. Return `404 current_learner_not_found` when there are none, or `409 current_learner_ambiguous` when there are multiple learners. This read never creates or arbitrarily selects a learner. |

Success response:

```json
{"learner_id": 1, "display_name": null}
```

The response exposes only the learner reference required by existing progress routes and the optional display name. The integer is a learner resource ID already used in the API path; no timestamps, source payload, or other database details are returned. `current_learner_ambiguous` includes `learner_count` in `details`. This endpoint does not introduce learner selection, profile management, or authentication.

### Learner progress

| Method and path | Purpose |
|---|---|
| `GET /api/v1/curriculum/releases/{release_id}/learners/{learner_id}/progress` | Return explicit progress rows only for Topics present in the selected release. Optional status filters can be added without changing the record shape. |
| `GET /api/v1/curriculum/releases/{release_id}/learners/{learner_id}/progress/{topic_id}` | Return `{ "progress": null }` when no row exists, or the stored record. The release is used to verify that the Topic belongs to the requested snapshot. |
| `PATCH /api/v1/curriculum/releases/{release_id}/learners/{learner_id}/progress/{topic_id}` | Independently update status, confidence, scope, or notes. Omitted fields remain unchanged; explicit null clears that field when the resulting record still has status or confidence. Every effective change appends a previous-state history snapshot in the same transaction. |
| `DELETE /api/v1/curriculum/releases/{release_id}/learners/{learner_id}/progress/{topic_id}` | Clear the current assessment. Preserve a before-change snapshot and all evidence/history, then remove the current row so subsequent reads/readiness see unassessed. |

PATCH requires at least one field to be supplied. Omitted means unchanged; an explicit null clears that one field. If both status and confidence would become null, reject PATCH with `422 use DELETE to clear the assessment`; DELETE is the one operation that clears both and restores the absent-row state. Creating a row requires a non-null status or confidence. A `notes`-only or `progress_scope`-only patch is allowed only when a progress row already exists. Clearing an already absent row is idempotent and creates no history entry because no state changed. A no-op PATCH likewise creates no history entry.

### Later, not in the initial frontend contract

Learner profile create/edit and evidence/history read endpoints can follow once local learner selection is decided. Progress mutation history semantics are defined below and are written by the current PATCH/DELETE service. Curriculum authoring, revision, validation, and publish routes are deliberately excluded; a future authoring service can be added behind separate routers and services without changing the read contract above.

## 4. Response and request schema outline

Response models should be distinct from ORM models and from the existing import models. Illustrative Pydantic v2 shapes:

```python
class ReleaseSummary(BaseModel):
    release_id: UUID           # Public immutable ID; never the DB integer key.
    curriculum_version: str
    schema_version: str       # Curriculum package schema version, not DB/Alembic version.
    status: str | None
    imported_at: datetime

class TopicSummary(BaseModel):
    id: str                   # Stable Topic ID
    title: str
    track_ids: list[str]
    phase_id: str | None
    current_priority: str | None
    metadata: dict[str, Any] = {}

class ObjectiveResponse(BaseModel):
    type: str | None
    text: str
    metadata: dict[str, Any] = {}

class PrerequisiteGroupResponse(BaseModel):
    group_ordinal: int
    logic_within_group: Literal["AND"]
    requires_all: list[str]

class TopicDetail(TopicSummary):
    description: str | None
    objectives: list[ObjectiveResponse]
    prerequisite_groups: list[PrerequisiteGroupResponse]
    related_topic_ids: list[str]

class GroupReadiness(BaseModel):
    group_ordinal: int
    readiness: Literal["ready", "not_ready", "unknown"]
    satisfied_topic_ids: list[str]
    not_satisfied_topic_ids: list[str]
    unknown_topic_ids: list[str]

class ReadinessResponse(BaseModel):
    topic_id: str
    readiness: Literal["ready", "not_ready", "unknown"]
    ready: bool | None
    has_satisfied_group: bool
    groups: list[GroupReadiness]

class ProgressResponse(BaseModel):
    topic_id: str
    progress_status: Literal["Not started", "Learning", "Practicing", "Solid", "Revisit"] | None
    confidence: int | None       # 1..5; independent of progress_status
    progress_scope: str | None
    notes: str | None
    updated_at: datetime

class ProgressEnvelope(BaseModel):
    progress: ProgressResponse | None

class ProgressPatch(BaseModel):
    progress_status: Literal["Not started", "Learning", "Practicing", "Solid", "Revisit"] | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)
    progress_scope: str | None = None
    notes: str | None = None

class ActiveReleaseSelection(BaseModel):
    release_id: UUID
```

For PATCH, validate `model_fields_set` so at least one property was supplied and update only supplied values. Validate the resulting status/confidence pair against the existing database constraint; if both would be null, direct the client to DELETE. When no progress row exists, require non-null `progress_status` or `confidence`; notes/scope alone cannot create an unassessed row. For an existing row, notes/scope can be updated independently. A `ProgressResponse` with `progress_status="Not started"` is distinct from `ProgressEnvelope(progress=None)`. Avoid mutable defaults in concrete Pydantic code by using `Field(default_factory=dict)`.

The dependencies response could have this compact shape:

```json
{
  "topic_id": "CS-001",
  "prerequisite_groups": [
    {"group_ordinal": 0, "logic_within_group": "AND", "requires_all": ["MATH-001", "CS-002"]},
    {"group_ordinal": 1, "logic_within_group": "AND", "requires_all": ["ALT-003"]}
  ],
  "group_logic": "OR",
  "direct_dependent_ids": ["ML-004"],
  "ancestor_ids": ["CS-002", "MATH-001"],
  "downstream_dependent_ids": ["ML-004", "ML-008"],
  "related_topic_ids": ["STAT-002"]
}
```

Readiness response example, including uncertainty:

```json
{
  "topic_id": "ML-004",
  "readiness": "unknown",
  "ready": null,
  "has_satisfied_group": false,
  "groups": [
    {
      "group_ordinal": 0,
      "readiness": "not_ready",
      "satisfied_topic_ids": ["CS-001"],
      "not_satisfied_topic_ids": ["MATH-001"],
      "unknown_topic_ids": []
    },
    {
      "group_ordinal": 1,
      "readiness": "unknown",
      "satisfied_topic_ids": [],
      "not_satisfied_topic_ids": [],
      "unknown_topic_ids": ["ALT-003"]
    }
  ]
}
```

## 5. Error convention

Use one envelope for handled errors:

```json
{"error": {"code": "topic_not_found", "message": "Topic 'CS-999' is not in this release", "details": {}}}
```

| HTTP | Cases |
|---|---|
| `400` | Malformed cursor or unsupported query parameter. |
| `404` | Unknown public release UUID, learner, or Topic not present in the selected release. |
| `409` | No active release has been selected; progress state conflict if concurrency control is later added. |
| `422` | Pydantic request validation, invalid progress status/confidence, empty PATCH, or invalid combination. |
| `500` | Unexpected server failure; do not return SQL or traceback details. |

Normalize FastAPI request-validation errors into the same envelope in an exception handler. Database integrity errors should be mapped only where the service knows the violated business rule; otherwise return a generic `500` and log locally.

## 6. Scope and semantics

- A release is resolved by public UUID first. Every curriculum table query must include that resolved release. A stable Topic ID that exists in another release but not this one returns `404` in this release context. The active-release pointer references an internal release row but the API returns its public UUID.
- Learner progress itself is keyed globally by `(learner_id, topic_id)`, not by release. Progress list queries must join/filter to Topic IDs in the requested release. The API must never copy state to a replacement Topic or synthesize missing rows.
- The API should expose `learner_id` as a resource reference and treat it as opaque in frontend code. Current storage uses an integer surrogate key; response models must not expose other ORM keys.
- Progress reads return only extant rows. An absent record remains absent. A stored explicit `Not started` remains a record. Confidence is serialized independently. Each effective mutation writes a before-image to `ProgressHistory` before changing/deleting the current row, within the same transaction. For an absent prior row, record null assessment fields and an explicit event type such as `api_before_change_unassessed`; for an existing row, snapshot its status, confidence, scope, and notes. Status-only and confidence-only updates preserve the other current field. DELETE snapshots then removes only `LearnerProgress`; it does not delete `LearnerEvidence`, `ProgressHistory`, or history-evidence links.
- Current dependency truth is `Solid` only. Reuse `DependencyEngine`; never implement a second evaluator in route code.
- Related Topics remain their own field and must not be merged into prerequisite group or graph results.

## 7. Proposed backend module structure

```text
backend/app/
  main.py                 # FastAPI app, lifespan, exception handlers
  api/
    deps.py               # DB session and request dependency helpers
    errors.py             # Public API error envelope and exception mapping
    routes/
      curriculum.py       # Releases, tracks, phases, topics, hierarchy
      dependencies.py     # Dependency graph and readiness routes
      learner_progress.py # Read/list/patch learner progress
  schemas/
    api_common.py         # Error, pagination, metadata shapes
    curriculum_api.py     # Read response schemas
    learner_api.py        # Progress read/PATCH schemas
  services/
    curriculum_queries.py # Release-scoped view assembly and filtering
    progress_service.py   # Learner-scoped, transactional progress reads/writes
    release_resolver.py   # Public release UUID -> internal release lookup
    release_selection.py  # Transactional read/write for the singleton active pointer
  db/                     # Existing models, database, initialization
  dependency.py           # Existing dependency business logic, reused
  importer.py             # Existing package validation/import CLI
```

Route handlers should parse/validate request and path parameters, call a service, and serialize a response model. Services own release/learner/Topic validation and query assembly. Readiness service calls `DependencyEngine`; progress service owns the transaction and does not mutate on GET. Active selection validates the candidate release and atomically changes the pointer without changing its `release_status`. No route should call the ZIP importer or Alembic directly.

Use a FastAPI yield dependency backed by `make_session_factory`, closing the Session after each request. Engine and factory can be created once for the app lifespan. Database upgrade should remain an explicit setup/startup choice consistent with current `initialize_database()`; do not silently create or migrate the database in individual requests.

## 8. Initial frontend endpoint priority

**Essential first slice:**

1. `GET /curriculum/releases`, explicit active-release selection during setup, and release-scoped Tracks, Phases, Topics, and Topic detail/hierarchy.
2. `GET .../topics/{topic_id}/dependencies` and learner-scoped readiness.
3. Learner progress list/detail and PATCH, preserving absent rows and independent fields.

**Can wait:**

- Current-release shortcut is available only after setup selects a release. Until then, the frontend can select a release explicitly from the release list, but curriculum views and readiness still require an explicit release UUID.
- Learner profile editing/management, evidence APIs, and progress-history APIs.
- Cursor sophistication if the frontend first consumes the entire small local collection.
- All curriculum authoring, validation, revision, and publication endpoints.

## 9. Required schema migration and remaining API decisions

### Implemented schema migration

The existing schema does **not** support either requested release behavior. Add one Alembic migration after current head `24d9c72cc7f1` with the smallest two changes:

1. Add `curriculum_release.public_id`, a unique UUID string (36-character canonical form). Migration backfills every existing release with a generated UUID. New releases receive a UUID once at creation. A unique index plus SQLite insert/update triggers enforce uniqueness, non-null behavior, and immutability without rebuilding the referenced `curriculum_release` table. This ID is independent of `curriculum_version`, curriculum `schema_version`, source digest, and the internal integer `id`.
2. Add a singleton `active_curriculum_release` pointer table. A `singleton_id` constrained to the sole value `1` is the primary key; a unique non-null `release_id` foreign key references `curriculum_release.id` with deletion restricted while selected. The table may contain zero rows before setup, or exactly one row after selection. Updating its row is the only way to change the active release. It is independent of free-text `release_status`.

The migration preserves all existing release data and does not select the v3.0.0 candidate automatically. After migration, an explicit setup call to `PUT /api/v1/curriculum/active-release` selects the UUID returned by the release-list endpoint. No curriculum-version or schema-version fields are repurposed. Since SQLite cannot safely rebuild this parent table while its existing foreign keys are enabled, the additive UUID column is physically nullable but the migration's triggers reject null/empty inserts and updates; this preserves the effective non-null contract without weakening foreign-key enforcement.

### Progress history assessment

No history migration is required for the agreed behavior. `ProgressHistory` already has learner/Topic identity, nullable `progress_status` and `confidence`, scope, notes, source release, event type, timestamp, and source payload. Its check permits null/null historical snapshots; only `LearnerProgress` requires at least one of status/confidence. The existing model is therefore sufficient to preserve a before-image and represent the prior unassessed state. API mutations should append the before-image before updating or deleting `LearnerProgress`, in the same transaction. Use distinct event types for package import snapshots and API before-change snapshots. Learner evidence remains in its own tables and is never used as the audit log.

### Remaining contract details

1. **Learner selection is only minimally modeled.** There is no public learner UUID or profile workflow; current data has one unnamed learner. Decide whether the local frontend selects from a learner list, uses a configured default, or creates profiles later. Do not assume a learner when multiple exist. This does not block defining progress routes with an opaque-in-client `learner_id` resource path.
2. **Import schema is not an API response contract.** The existing schemas are intentionally open for import compatibility. Build separate, explicit response/PATCH schemas instead of exposing `source_payload` or reusing import models wholesale.
3. **Mutation history event policy should be implemented exactly as above.** Snapshot the prior persisted state for every effective change. For a first assessment, write a null/null unassessed before-image with the explicit `api_before_change_unassessed` event type. A no-op mutation writes no history. Clearing via DELETE snapshots the prior state then deletes only the current row; repeated clearing is a no-op.

4. **Validation gate for future authored releases.** Current package import validates before inserting a release, and its validation report is retained in release provenance. The schema has no normalized validation result/status. The active-selection service can rely on the validated importer for current imported releases; a future authoring layer must provide a validation result and block activation until that validation passes.

These are implementation requirements, not contradictions in the imported curriculum or dependency semantics. Read endpoints and dependency evaluation fit the existing schema. Active selection and stable public release identifiers require the migration above; progress history and clearing fit the existing history/current-state tables without a migration.
