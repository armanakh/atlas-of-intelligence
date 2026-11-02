# Atlas of Intelligence frontend

React, TypeScript and Vite client for the local First-Principles AI Curriculum Explorer API.

## Run locally

From the repository root, start the API after initializing the database:

```powershell
uv run python -m app.db.initialize
uv run uvicorn app.main:app --app-dir backend --reload
```

Then, in `frontend/`:

```powershell
pnpm install
pnpm dev
```

Open `http://127.0.0.1:5173`. The client uses `http://127.0.0.1:8000` by default. Set `VITE_API_BASE_URL` in a local `.env` file to use another local API URL.

The imported curriculum is not automatically active. Choose a release in the header; this calls the explicit active-release selection endpoint. The app resolves the existing learner through `GET /api/v1/learners/current` and does not create one. If learner resolution is ambiguous or unavailable, curriculum browsing remains available while learner controls explain their unavailable state.

## Build

```powershell
pnpm build
```

The build runs the TypeScript compiler and creates the static Vite bundle in `dist/`.
