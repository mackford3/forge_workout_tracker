# FORGE — Workout Tracker

A mobile-first, self-hosted workout tracking app built with Flask + HTMX + PostgreSQL.
Designed to run on Unraid and be used at the gym from your phone.

---

## Features

- **Dashboard** — YTD stats, streaks (current + best), last workout, active plan. Tap streaks to open calendar.
- **5 workout types** — Strength, Run, Hyrox, Circuit, AMRAP
- **Strength logging** — Exercises grouped horizontally by set, shows last session + PR on exercise select, inline cardio sets
- **Run logging** — Continuous, timed, or interval runs with per-segment tracking (warmup/interval/cooldown), skip flags
- **Circuit & AMRAP** — Per-round data per exercise (reps, weight, time, distance, steps)
- **Hyrox** — Full race logging with all 16 stations
- **Edit any workout** — Full edit UI for all workout types, pre-filled with existing data
- **Workout view** — PR badges on sets, estimated 1RM per exercise (Epley formula)
- **Progress tracker** — Strength: Max Weight / Volume / Est. 1RM charts per exercise. Runs: Distance + Pace charts with segment fallback for intervals
- **Calendar** — Monthly view with color-coded workout days, multi-workout day modal, month summary (sessions, active days, PRs, km run, lbs lifted)
- **Exercise library** — Filter by muscle group, add custom exercises
- **Training plans** — Build multi-week plans with named days
- **Data export** — CSV export of all workouts, strength sets, and runs
- **lbs / kg toggle** — Top bar toggle, both units always stored in DB
- **Mobile-first UI** — Dark theme, bottom nav, sticky top bar, safe area insets for iPhone

---

## Tech Stack

| Layer     | Tech                           |
|-----------|--------------------------------|
| Backend   | Python 3.11 + Flask 3          |
| Database  | PostgreSQL 16 (`forge` schema) |
| Frontend  | HTMX + vanilla JS + Chart.js   |
| Fonts     | Bebas Neue, DM Sans, DM Mono   |
| Hosting   | Docker Compose on Unraid       |

---

## Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 16 running locally
- (Optional) DBeaver for DB inspection

### Setup

```bash
# 1. Clone and create venv
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Create the database (connect to 'postgres' db in DBeaver or psql)
psql -U postgres -f migrations/create_db.sql

# 3. Run the schema + seed data (connect to 'forge_workouts' db)
psql -U postgres -d forge_workouts -f migrations/init.sql

# 4. Configure environment
cp .env.local .env
# Edit .env — set DB_PASS to your postgres password

# 5. Run
flask run
# → http://localhost:5000
```

### DBeaver Tips
- Run `create_db.sql` with **Auto-Commit ON**, connected to the `postgres` database
- Run `init.sql` connected to the `forge_workouts` database
- If pgAgent error appears: Edit Connection → PostgreSQL tab → uncheck "Show pgAgent jobs"
- If database not visible: Edit Connection → PostgreSQL tab → enable "Show all databases"

---

## Unraid Deployment

```bash
# Copy project to appdata
scp -r workout-tracker/ root@UNRAID_IP:/mnt/user/appdata/

# SSH in and start
ssh root@UNRAID_IP
cd /mnt/user/appdata/workout-tracker
cp .env.example .env   # fill in passwords
docker compose up -d
```

Access at `http://YOUR_UNRAID_IP:5000`

### Migrate local data to Unraid

```bash
# Dump local DB
pg_dump -U postgres forge_workouts > forge_backup.sql

# Restore on Unraid
cat forge_backup.sql | docker exec -i workout_db psql -U postgres forge_workouts
```

### Update

```bash
docker compose pull
docker compose up -d --build
```

---

## Project Structure

```
forge_workout_tracker/
├── wsgi.py
├── requirements.txt
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── migrations/
│   ├── create_db.sql        # Run first — creates forge_workouts database
│   └── init.sql             # Schema + exercise library + 16 historical workouts
└── app/
    ├── __init__.py          # App factory, DB config, blueprints
    ├── models.py            # SQLAlchemy models (13 tables)
    ├── utils.py             # lbs↔kg helpers
    ├── routes/
    │   ├── main.py          # Dashboard, streaks, calendar
    │   ├── workouts.py      # Log, view, edit, delete, history, CSV export
    │   ├── progress.py      # Strength + run chart data APIs
    │   ├── plans.py         # Training plans
    │   └── exercises.py     # Exercise library
    └── templates/
        ├── base.html        # Layout, nav, log modal, unit toggle
        ├── index.html       # Dashboard
        ├── calendar.html    # Monthly calendar view
        ├── progress/
        │   └── index.html   # Strength (weight/volume/1RM) + run charts
        ├── workouts/
        │   ├── history.html
        │   ├── view.html    # PR badges, 1RM estimates
        │   ├── edit.html
        │   ├── log_strength.html
        │   ├── log_run.html
        │   ├── log_circuit.html
        │   └── log_hyrox.html
        ├── plans/
        ├── exercises/
        └── partials/
            ├── exercise_history.html  # Last session + PR strip
            ├── set_row.html
            ├── interval_row.html
            ├── circuit_exercise_row.html
            └── plan_day_row.html
```

---

## Database Schema

All tables live in the `forge` schema inside the `forge_workouts` database.

| Table                  | Purpose                                      |
|------------------------|----------------------------------------------|
| `workouts`             | Session header (type, date, location, stats) |
| `workout_sets`         | Strength sets (weight, reps, steps, RPE)     |
| `cardio_sets`          | Row/SkiErg/Assault Bike sets                 |
| `runs`                 | Run session header                           |
| `run_segments`         | Warmup / interval / cooldown splits          |
| `hyrox_results`        | Hyrox race header                            |
| `hyrox_stations`       | Per-station time + details                   |
| `circuits`             | Circuit/AMRAP header                         |
| `circuit_exercises`    | Exercise list within a circuit               |
| `circuit_round_sets`   | Per-round data per exercise                  |
| `exercises`            | Exercise library                             |
| `workout_plans`        | Training plan                                |
| `plan_days`            | Days within a plan                           |

---

## Environment Variables

| Variable      | Default          | Description                 |
|---------------|------------------|-----------------------------|
| `DB_USER`     | `postgres`       | Postgres username            |
| `DB_PASS`     | —                | Postgres password            |
| `DB_HOST`     | `localhost`      | Postgres host                |
| `DB_PORT`     | `5432`           | Postgres port                |
| `DB_NAME`     | `forge_workouts` | Database name                |
| `DB_SCHEMA`   | `forge`          | Postgres schema              |
| `SECRET_KEY`  | —                | Flask session secret         |
| `WEIGHT_UNIT` | `lbs`            | Default unit (`lbs` or `kg`) |

---

## Future Features

- [ ] **Create custom program** — UI to build a new structured program from scratch with options for: program length (weeks), goal selection (strength, endurance, hyrox, general fitness), days per week, phase structure, and deload weeks. Currently programs must be added via SQL.
- [ ] **Create custom plan** — A plan is a shorter, lighter version of a program — a repeating weekly split (e.g. "Push/Pull/Legs 3x/week") without phases or progression tracking. Build it in the Plans tab and optionally set it active to see it in the log modal.
- [ ] **Garmin sync** — Import `.fit` files via `fitparse` + `garminconnect` Python libraries. Would auto-populate run sessions with HR, pace splits, and GPS data from Garmin Connect without manual entry.
- [ ] **Workout templates** — Save a logged workout as a reusable template, then start a new session pre-filled with the same exercises and sets. Big gym QoL improvement.
- [ ] **Hyrox race comparison** — Side-by-side station breakdown across multiple races to track splits over time.
- [ ] **Unraid Docker template** — One-click install via Unraid Community Applications.