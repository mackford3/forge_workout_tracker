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

## Future Enhancements

Design and UX improvements identified for future iterations:

### ✅ Resolved

**Weight unit toggle without reload** — Dashboard weight stat now stores both lbs and kg as `data-lbs`/`data-kg` attributes. Toggling the unit button swaps all labelled values in the DOM instantly — no page reload.

**Context-aware dashboard header** — The dashboard `h1` and subtitle are now dynamic: 7+ day streak shows "X DAYS 🔥 / You're on fire", 3–6 day streak shows "X-DAY STREAK", trained today shows "GREAT WORK", otherwise falls back to year stats with the next program day name as subtitle.

**Workout type breakdown chart** — The badge row is now preceded by a proportional stacked bar: each workout type gets a flex segment in its brand colour (`--strength`, `--run`, `--hyrox`, etc.), followed by the existing badge row below. Hidden when there are no workouts.

**Delete from history rows (swipe-to-delete)** — Each history row is wrapped in a swipe container. On mobile, swipe left > 60px reveals a red delete zone; tapping the trash icon shows an inline Cancel / Yes, Delete confirmation. Desktop users can also tap the trash icon that appears on the right side of the revealed zone.

### Open

- [ ] **Autosave / data-loss protection** — Persist in-progress log form state to `localStorage` so a browser refresh, accidental navigation, or app switch doesn't wipe unsaved sets. Restore on next visit with a banner offering to resume or discard.
- [ ] **"Log again" shortcut from history** — A button on each workout history row (or on the workout view page) that opens the log form pre-filled with the same exercises, sets, and session config from that workout.
- [ ] **History search and filter** — Add a search box and type/date filters to the workout history page so specific sessions can be found quickly as history grows.
- [ ] **History pagination (load more)** — Replace full list rendering with an initial page of ~20 workouts and an "Load More" button or infinite scroll, so the history page stays fast at scale.
- [ ] **add premade workouts for hyrox sims**
- [ ] **add premade workouts for circuits**
- [ ] **add premade workouts for strength**
- [ ] **add premade plan for smolov jr  squats and Bench**


## Focused Testing Results — Hyrox

### ✅ Resolved

**Race vs. Training split** — The Hyrox entry point is now a dedicated selection page (`hyrox_select.html`) with a Race / Training tab toggle. Race mode logs all 16 stations in official order. Training mode offers five presets: Full Simulation, Half Sim A, Half Sim B, Workouts Only, and Running Only — each with a fixed station subset. The logger header and badge correctly reflect the mode (RACE / TRAINING) and the form submit button updates accordingly.

**Duration / Calories / BPM prominence** — These three fields now appear in a single 3-column grid row on both the race and training log forms. No longer buried under Duration alone.

**Race type pre-selection** — The Start Race button URL updates live as the user selects Singles / Doubles / Relay, so the correct race type is passed through to the logger without an extra step.

**Hyrox days route from program week view** — `start_day` now detects day names containing "hyrox" and redirects to the Hyrox training logger instead of the strength form. Preset is inferred from the day name (half sim A/B, station practice, running only, full sim). The `program_day_id` is threaded through as a hidden field and linked on save, so the program completion is recorded exactly the same way as a strength day.

**PFT benchmark pre-fill from last attempt** — The log form now fetches the most recent `PremadeResult` and passes its per-station times to the template. Each station shows a "Last: X:XX" chip next to the Skip toggle, and the time input placeholder is set to the previous split so the target is visible before the athlete types anything.

**Benchmark progress chart Y-axis label** — The Y-axis now shows "Total Time (lower = faster)" so the inverted direction is self-explanatory on first view.

---

**Training preset stations: skip toggle** — Each station card in training mode now has a Skip checkbox. Checking it dims the row and submits `stations[i][skipped]=1`. The `_save_hyrox_stations` helper skips any flagged station, so partial simulations log cleanly without empty station records.

**Circuit/AMRAP header** — The header and subtitle are now conditional on `circuit_type`. Circuit shows "🔄 CIRCUIT / Structured Circuit Training"; AMRAP shows "⚡ AMRAP / As Many Rounds As Possible".

**Circuit Add Exercise** — The HTMX `hx-get` dependency is removed. Exercises are embedded as a JSON array at page load and `addExercise()` builds the full row in vanilla JS using `insertAdjacentHTML`. Works offline and on flaky mobile data, identical to how the strength logger behaves.

---



## Resolved for Strength

**History pre-fill race condition** — `loadHistory` now fills ALL empty weight inputs in the sets-row after the fetch completes, not just the first one. Sets added before the fetch resolves get backfilled when history arrives.

**Add Set scroll isolation** — The "+ Add Set" button is now a flex item inside the horizontal scroll row, rendered as a `+` card. It scrolls with the sets so it's always visible next to the last set regardless of how many sets are present.

**Exercise reorder** — Each exercise block header now has ↑/↓ arrow buttons. Tapping ↑/↓ moves the block up or down in the exercises container using `insertBefore`, so you can reorder at any time without removing and re-adding.

**Session-level RPE** — A "Session RPE" field (1–10, step 0.5) now appears in the session info card alongside Duration, Calories, and Avg BPM on all three strength forms (log, program start, edit). Stored in `workouts.session_rpe NUMERIC(3,1)`. **DB migration required — see SQL below.**

**Program exercise match failure indicator** — When `start_workout.html` pre-populates an exercise and the fuzzy match fails (exercise_id is null), the block gets an orange border and the program hint label shows "⚠ not found — select manually" in orange, making the failure impossible to miss.

**Exercise search/filter on progress page** — A text filter input above the exercise dropdown on the Strength progress tab filters options in real time by exercise name or muscle group. Matching is case-insensitive across both the option text and the `data-group` attribute.

**1RM empty state explanation** — When the Est. 1RM tab is selected with only 1 session logged, the empty state now shows: "Log at least 2 sessions to see your Est. 1RM trend. Your current estimate: X lbs." instead of a blank chart with no context.

**Edit workout program link** — Investigated: the program completion link is preserved through edits. Changing `workout_type` in edit does not touch `ProgramCompletion` records (linked by `workout_id`, not type). No breaking behavior confirmed — resolved as false positive.

---

### DB Migration Required


