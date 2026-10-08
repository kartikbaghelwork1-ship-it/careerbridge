# CareerBridge — complete runnable project

## Start
Requires Python 3.10+ and an internet connection for the first dependency installation.

    python3 run.py

Windows: `py run.py`. Open http://127.0.0.1:8000.

The launcher creates a project-local .venv, installs dependencies and starts the frontend and backend together. No API key needed. Do not open index.html directly for account features.

Click **Sign in / Register**, enter an email and a password of 10–128 characters, and create your account. Registration saves your current workspace. Subsequent sign-ins load that account's data. Guest work lasts only while the page is open.

## Working features
- Animated responsive landing page with section navigation and scroll reveals
- Account registration, sign-in, sign-out and seven-day cookie sessions
- Editable academic profile and interest-based career ranking
- Four career paths, skill-gap analysis and milestone roadmaps
- Learning-resource directory
- Searchable sample internship/job cards and per-account shortlist
- Resume text checklist and download
- Four mock interview questions with structured feedback
- Official government employment discovery links
- Per-account database persistence for profile, milestones, shortlist, resume and interview drafts
- JSON export and workspace reset

Career matching, resume review and interview feedback are free rule-based features. A live LLM, live vacancy feed, PDF parser, email verification and password-reset email service are not connected. Job listings are clearly marked samples; resource links lead to real external websites. This scope is deliberate and visible in the app.

## Database
Created automatically at backend/data/careerbridge.sqlite3. No manual database configuration is needed locally. Backup this file while the server is stopped. CAREERBRIDGE_DB can override its path. The ZIP excludes all database records and credentials.

Account data is not stored in localStorage. The frontend saves to authenticated API routes with an explicit save status and retry control. SQLite queries are parameterized and restricted to the signed-in user. Passwords are scrypt hashes with per-user random salts; session tokens are stored hashed. Login/register attempts are rate limited. Write requests enforce origin and JSON headers. Multi-tab edits use last-write-wins.

## Manual environment setup

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    .venv/bin/python backend/server.py

Windows Python executable: .venv\Scripts\python.exe

## Tests

    .venv/bin/python -m unittest discover -s tests -v

Six integration checks cover sign-in/logout, persistence after app restart, account isolation, matching, invalid inputs, cross-site requests, login throttling, private-file access and hashed credentials.

## Optional production packaging
Dockerfile, compose.yaml and wsgi.py are supplied for later deployment. `docker compose up --build` runs the app with Gunicorn and a persistent database volume. Docker is optional and this environment has not run that image.
For a future HTTPS deployment set APP_ORIGIN to the exact canonical HTTPS origin and SECURE_COOKIES=true behind a trusted TLS endpoint. Do not expose the Flask development server directly. The Gunicorn build has one worker and four threads; use a shared production database before horizontal scaling.

## API
GET /api/health
POST /api/auth/register — {email,password}
POST /api/auth/login — {email,password}
POST /api/auth/logout — {}
GET /api/auth/me
GET /api/state
PUT /api/state — workspace state
GET /api/recommendations

Mutations require Content-Type: application/json and X-CareerBridge: 1. Session cookies are sent on same-origin requests.

## Source
Frontend: dist/index.html, dist/style.css, dist/app.js, dist/backend.js
Backend: backend/app.py, backend/core.py, backend/server.py
Tests: tests/test_app.py
Launcher: run.py

No deployment or domain/DNS changes were made for this version. The older live demo is separate.
