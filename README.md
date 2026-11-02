# Atlas of Intelligence

Atlas is a local-first application for exploring a curriculum as an interconnected knowledge map. Browse Tracks, Phases, and Topics; inspect objectives and prerequisite paths; and record learning status and confidence independently. Readiness is informative and does not restrict what you can study.

## What the application includes

- A React, TypeScript, and Vite web client.
- A Python and FastAPI local API.
- SQLite persistence through SQLAlchemy 2.x and Alembic migrations.
- A validated curriculum ZIP importer and a read-only prerequisite evaluation engine.
- Local learner progress, confidence, evidence, and progress history.

The app does not require an account, cloud service, or hosted API for basic local use. The API and development frontend bind to loopback addresses by default. No curriculum archive is included in this repository.

## Current curriculum onboarding limitation

There is no curriculum authoring screen, package builder, CSV importer, or generic unvalidated JSON import. The current importer accepts a validated ZIP in the First-Principles curriculum package contract. To use another curriculum, prepare a ZIP that follows this contract and passes its validation rules; see [the import schema](backend/app/schemas/curriculum.py) and [the package validator](backend/app/importer.py).

The ZIP must contain exactly these files:

- curriculum_registry.json — curriculum/schema versions, Tracks, Phases, Topics, objectives, stable Topic IDs, migration entries, and reserved IDs.
- dependency_registry.json — a prerequisite-group decision for each Topic and separate Related Topic links.
- learner_progress.json — the importing learner's progress records and evidence. For a fresh learner, use empty records and evidence_records arrays and set the unassessed count to the number of Topics.
- validation_report.json — validation results and counts that agree with the curriculum and dependency registries.
- README.md and CODEX_HANDOFF.md — package documentation/provenance required by the current contract.

The importer creates a local learner when the database has none. It then imports the learner data in the ZIP. Use an empty learner section for a fresh assessment history; never import another person's progress or evidence. On an already used database, conflicting learner data is rejected instead of overwriting current progress. If multiple learners already exist, provide --learner-id to the importer; the app does not currently offer learner selection.

## Prerequisites

- Git.
- Python 3.11 or newer.
- [uv](https://docs.astral.sh/uv/).
- Node.js 22.12 or newer. This satisfies the Vite 7 requirement and the frontend test runner. See [Vite's Node.js compatibility note](https://vite.dev/guide/).
- pnpm 11. Install it with npm install --global pnpm@11 if it is not already available. See [pnpm installation](https://pnpm.io/installation).

## Clone and install

Replace the placeholder with the GitHub URL after the project is published.

~~~powershell
git clone <repository-url> atlas-of-intelligence
Set-Location atlas-of-intelligence
uv sync --extra dev --locked
Push-Location frontend
pnpm install --frozen-lockfile
Pop-Location
~~~

uv sync installs the backend and test dependencies into the project environment. pnpm install uses the committed lockfile.

## Local configuration

Defaults are suitable for a local run. From the repository root, the backend uses sqlite:///./data/curriculum.db; the relative path is resolved from the process working directory.

To select another SQLite database or change allowed local frontend origins, set these variables in the PowerShell session used to run the backend:

~~~powershell
$env:DATABASE_URL = "sqlite:///./data/curriculum.db"
$env:API_CORS_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173"
~~~

The default frontend API URL is http://127.0.0.1:8000. To override it, create frontend/.env.local (this file is ignored by Git):

~~~dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
~~~

The backend reads DATABASE_URL and API_CORS_ORIGINS from its process environment; it does not automatically load a root .env file. These examples contain local addresses and placeholders only. No credentials are needed.

## Initialize a fresh database

From the repository root:

~~~powershell
uv run python -m app.db.initialize
~~~

This creates the default data/curriculum.db file and applies all Alembic migrations. The command is safe to repeat. The entire data/ directory is excluded from Git.

You can start the API and frontend with an empty database, but the map will have no curriculum release or learner yet. Import a valid curriculum package first to browse Topics and record progress.

## Import your curriculum and learner data

Keep your ZIP outside the repository. From the repository root, substitute the path to your own compatible package:

~~~powershell
$packagePath = "C:\path\to\your-curriculum-package.zip"
uv run python -m app.importer $packagePath --report-out reports/curriculum_import_report.json
~~~

The importer validates all package files and references before writing. It upgrades the schema and imports the release and the ZIP's learner data in one transaction. On a new database it also creates a local learner without inventing a display name. A fresh package should contain empty progress/evidence arrays so every Topic remains unassessed. Reports may contain learner/evidence counts and are ignored by Git; do not publish reports generated from personal data.

An imported release is not automatically active. After starting the frontend, choose the release in the Edition selector in the header. Only then will it appear as the current map. The release selector calls the explicit active-release API.

## Start Atlas

Open two terminals from the repository.

**Terminal 1 — API** (from the repository root):

~~~powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
~~~

The API is at http://127.0.0.1:8000; its interactive OpenAPI documentation is at http://127.0.0.1:8000/docs.

**Terminal 2 — frontend**:

~~~powershell
Set-Location frontend
pnpm dev
~~~

Open http://127.0.0.1:5173. Select the imported release from the header. The UI resolves the existing local learner through GET /api/v1/learners/current; that GET never creates a learner. After import, open an Idea to assess its learning status and confidence independently. Missing progress records remain unassessed; the UI does not create Not started assessments merely by browsing.

The API and Vite server bind to 127.0.0.1 by default. Changing VITE_API_BASE_URL to a remote host is optional and outside the default local-only setup.

## Run tests and build

From the repository root:

~~~powershell
uv run --extra dev pytest -p no:cacheprovider
~~~

From frontend/:

~~~powershell
pnpm test:atlas
pnpm build
~~~

Tests that validate the complete curriculum archive are skipped when it is not present. To run those checks with your own compatible package, set its local path before running pytest:

~~~powershell
$env:ATLAS_TEST_CURRICULUM_PACKAGE = "C:\path\to\your-curriculum-package.zip"
uv run --extra dev pytest -p no:cacheprovider
~~~

Do not add a personal curriculum archive to Git.

## Local data and backups

The default SQLite database at data/curriculum.db holds curriculum snapshots, learner progress, confidence, evidence, and progress history. If you set DATABASE_URL, back up the database at that path instead. Curriculum ZIPs and generated reports are separate files and are not needed for normal browsing after import.

To back up personal learning data, stop the API cleanly and copy the database file to a private backup location outside the repository. Keep backups encrypted or otherwise protected if appropriate for your device. To restore, stop the API and replace the database file with the backup. Never commit the database or a backup to Git.

## Data model and readiness semantics

Curriculum version and schema version are stored independently. Releases are immutable snapshots with public UUIDs; the active release is an explicit zero-or-one pointer. A migration never activates a release automatically.

Track membership and Phase placement are separate. A Topic has one stable identity, one Phase placement per release, and can belong to multiple Tracks. Optional curriculum metadata is retained in source payloads. Prerequisite groups are OR alternatives; Topics within each requires_all group are ANDed. Related Topics are stored separately and never affect readiness.

A prerequisite is satisfied only by Solid. Other recorded progress states are unsatisfied; a missing assessment is unknown. Confidence does not affect readiness. Phase and Track placement are not readiness conditions. Progress is not transferred automatically when a Topic is retired or replaced.

For the full API design, see [API_CONTRACT_PROPOSAL.md](API_CONTRACT_PROPOSAL.md). The frontend setup notes are in [frontend/README.md](frontend/README.md).
