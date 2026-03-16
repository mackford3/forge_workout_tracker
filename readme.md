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

## Focused Testing Results
🔥 Agent 1 — Hyrox/Circuit Athlete
Overall: The Hyrox full race logger is well built — 16 stations, split times, race type. The PFT/benchmark flow is a genuinely useful idea. But there are friction points that would frustrate someone logging mid-race or right after.
Issues found:
1. Hyrox logger shows "Log Hyrox" but the header says it's for "race or training session" — these are very different things. A race has 16 stations in fixed order. A training simulation (like your Hyrox Sim days in the program) might be 4 rounds of a subset. Right now there's no way to log a partial simulation from the Hyrox screen — you'd have to use Circuit. That's confusing. Suggest adding a "Simulation" mode toggle that lets you skip stations.
2. The circuit/AMRAP logger always says "⚡ AMRAP" in the header even when you select Circuit from the log modal. The title doesn't update — it's hardcoded. Small but jarring.
3. Circuit logging requires HTMX to add exercises — the + Add Exercise button uses hx-get and fails silently if HTMX isn't loaded or has a network hiccup. At the gym on mobile data this is a real risk. Strength logging uses pure JS and always works.
4. No way to log a Hyrox training simulation from the program week view. The "▶ Start" button only pre-populates strength exercises. If Friday's session is "Hyrox-Specific Simulation," tapping Start dumps you into a strength form with a list of text exercises like "4 Rounds: 800m Run" — you can't actually log times against them. You'd need to start a Circuit manually instead.
5. PFT benchmark log form has no pre-fill from last attempt. When you go to log your second PFT, all the station time fields are blank. For a timed benchmark you'd want to see your previous splits as a reference target — "last time you did the row in 4:52, aim for sub 4:45."
6. The benchmark progress chart Y-axis says "lower = better" conceptually but the axis itself has no label. First time you see it the direction feels wrong.
7. Calories and BPM fields on the PFT log form are buried under Duration. For a race-style effort these matter and should be more prominent.

💪 Agent 2 — Strength Athlete
Overall: The strength logger is the most polished part of the app — set persistence, history strip, PR badges, 1RM estimates all work well. A few things break the flow at the gym.
Issues found:
1. The exercise history strip shows last session weight but the pre-fill only works if the strip HTML loads before you tap "Add Set." If you select an exercise and immediately tap Add Set before the fetch completes, the weight field is blank. On slow mobile data this happens constantly.
2. Set cards scroll horizontally but "Add Set" is below the scroll area. After 4-5 sets on a small phone the Add Set button is visually separate from the sets — you have to scroll right to see set 4, then scroll back left to find the button. The button should float or follow the scroll.
3. No way to reorder exercises once added. If you forget an exercise and add it later, it appears at the bottom. In a real workout you might superset exercises — there's no way to group or reorder them.
4. RPE is on every set but there's no session-level RPE or difficulty rating. After a brutal workout you want to mark "this was a 9/10 day" not just per-set RPE.
5. The "Start" button from the program week view pre-populates exercises by fuzzy-matching names, but if the match fails you get a blank exercise select. There's no visual indicator that the match failed — the label hint says "Program: Back Squat 4x8-10" but the select shows "Select exercise…" with no warning that it didn't find it.
6. Progress page strength charts don't show the exercise's muscle group. When scrolling the "Select Exercise" dropdown looking for Goblet Squat, the grouping by muscle helps, but if you don't know which group it's in you're scrolling blind. A search/filter box on the dropdown would help.
7. 1RM estimates show on the workout view but not in the progress chart. You can see "Est. 1RM: 185 lbs" on a specific workout, but the progress page's Est. 1RM tab should show how that estimate has trended — which it does, but only if you've logged the same exercise multiple times. First visit with a single session it shows nothing and gives no explanation.
8. Editing a workout that was started from the program doesn't re-link to the program day. If you log a workout via ▶ Start, it links to the program completion. If you then edit that workout, the link is preserved — but if the edit changes the workout_type the link can break silently.