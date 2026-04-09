from sqlalchemy import func
from flask import Blueprint, render_template, request, redirect, url_for, Response, session
import csv, io
from datetime import datetime
from ..models import (db, Workout, WorkoutSet, Exercise, Run, RunSegment,
                      CardioSet, HyroxResult, HyroxStation, HyroxStationSegment,
                      HYROX_DEFAULT_STATIONS, HYROX_TRAINING_PRESETS,
                      Circuit, CircuitExercise, CircuitRoundSet)
from ..utils import lbs_to_kg

workouts_bp = Blueprint('workouts', __name__)


def _htmx_or_redirect(url):
    """Return HX-Redirect for htmx requests, or a normal redirect otherwise."""
    if request.headers.get('HX-Request'):
        resp = Response('', 200)
        resp.headers['HX-Redirect'] = url
        return resp
    return redirect(url)

LOCATION_CHOICES = [
    ('gym',     '🏋️ Gym'),
    ('home',    '🏠 Home'),
    ('outdoor', '🌳 Outdoor'),
    ('other',   '📍 Other'),
]


# ── History ────────────────────────────────────────────────
@workouts_bp.route('/')
def history():
    page  = request.args.get('page', 1, type=int)
    wtype = request.args.get('type', '')
    query = Workout.query.order_by(Workout.completed_at.desc())
    if wtype:
        query = query.filter_by(workout_type=wtype)
    workouts = query.paginate(page=page, per_page=20)
    return render_template('workouts/history.html', workouts=workouts, wtype=wtype)


# ── View Single Workout ────────────────────────────────────
@workouts_bp.route('/<int:workout_id>')
def view(workout_id):
    workout = Workout.query.get_or_404(workout_id)

    # pr_map:  exercise_id -> best est. 1RM from workouts strictly BEFORE this one
    # pr_best: exercise_id -> best est. 1RM achieved in THIS workout
    # A set earns a PR badge only when its 1RM matches the workout best AND
    # beats the previous best — so at most one set per exercise gets the badge.
    pr_map  = {}
    pr_best = {}
    if workout.workout_type == 'strength':
        ex_ids = db.session.query(WorkoutSet.exercise_id).filter_by(
            workout_id=workout.id).distinct().all()
        for (ex_id,) in ex_ids:
            def _best_1rm(sets):
                best = 0.0
                for ws in sets:
                    r = ws.reps or 1
                    est = float(ws.weight_lbs) * (1 + r / 30.0)
                    if est > best:
                        best = est
                return best

            prev_sets = db.session.query(WorkoutSet.weight_lbs, WorkoutSet.reps)\
                .join(Workout)\
                .filter(
                    WorkoutSet.exercise_id == ex_id,
                    WorkoutSet.skipped == False,
                    WorkoutSet.weight_lbs.isnot(None),
                    Workout.completed_at < workout.completed_at,
                ).all()
            pr_map[ex_id] = _best_1rm(prev_sets)

            curr_sets = db.session.query(WorkoutSet.weight_lbs, WorkoutSet.reps)\
                .filter(
                    WorkoutSet.workout_id == workout.id,
                    WorkoutSet.exercise_id == ex_id,
                    WorkoutSet.skipped == False,
                    WorkoutSet.weight_lbs.isnot(None),
                ).all()
            pr_best[ex_id] = _best_1rm(curr_sets)

    # Check for linked premade result (benchmark workout)
    premade_result = None
    try:
        from ..models import PremadeResult, PremadeStation
        pr = PremadeResult.query.filter_by(workout_id=workout_id).first()
        if pr:
            station_results = {sr.station_id: sr for sr in pr.station_results.all()}
            stations = pr.premade_workout.stations.all()
            pr._station_results = station_results
            pr._stations = stations
            premade_result = pr
    except Exception:
        pass

    return render_template('workouts/view.html', workout=workout, pr_map=pr_map,
                           pr_best=pr_best, premade_result=premade_result,
                           weight_unit=session.get('weight_unit', 'lbs'))


# ── Delete ─────────────────────────────────────────────────
@workouts_bp.route('/<int:workout_id>/delete', methods=['POST'])
def delete(workout_id):
    workout = Workout.query.get_or_404(workout_id)
    db.session.delete(workout)
    db.session.commit()
    return redirect(url_for('workouts.history'))


# ── Log Strength ───────────────────────────────────────────
@workouts_bp.route('/log/strength', methods=['GET', 'POST'])
def log_strength():
    exercises = Exercise.query.order_by(Exercise.name).all()
    if request.method == 'POST':
        f = request.form
        workout = Workout(
            workout_type='strength',
            name=f.get('name', 'Strength Session'),
            location=f.get('location', 'gym'),
            duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,
            calories=int(f['calories']) if f.get('calories') else None,
            avg_bpm=int(f['avg_bpm']) if f.get('avg_bpm') else None,
            session_rpe=float(f['session_rpe']) if f.get('session_rpe') else None,
            notes=f.get('notes'),
            completed_at=datetime.fromisoformat(f['completed_at']) if f.get('completed_at') else datetime.utcnow()
        )
        db.session.add(workout)
        db.session.flush()

        # Collect all set indices from form (non-contiguous safe)
        set_indices = sorted(set(
            int(k.split('[')[1].split(']')[0])
            for k in f.keys() if k.startswith('sets[') and '[exercise_id]' in k
        ))
        for i in set_indices:
            ex_id = f.get(f'sets[{i}][exercise_id]')
            if not ex_id:
                continue
            weight_raw = f.get(f'sets[{i}][weight]') or None
            unit       = f.get(f'sets[{i}][unit]', 'lbs')
            weight_kg = weight_lbs = None
            if weight_raw:
                w = float(weight_raw)
                if unit == 'lbs':
                    weight_lbs = w
                    weight_kg  = lbs_to_kg(w)
                else:
                    weight_kg  = w
                    weight_lbs = w * 2.20462
            db.session.add(WorkoutSet(
                workout_id  = workout.id,
                exercise_id = int(ex_id),
                set_number  = int(f.get(f'sets[{i}][set_number]', i + 1)),
                weight_kg   = weight_kg,
                weight_lbs  = weight_lbs,
                reps        = int(f[f'sets[{i}][reps]']) if f.get(f'sets[{i}][reps]') else None,
                duration_s  = int(f[f'sets[{i}][duration_s]']) if f.get(f'sets[{i}][duration_s]') else None,
                rpe         = float(f[f'sets[{i}][rpe]']) if f.get(f'sets[{i}][rpe]') else None,
                notes       = f.get(f'sets[{i}][notes]'),
            ))

        # Inline cardio sets — collect all cardio indices non-contiguously
        cardio_indices = sorted(set(
            int(k.split('[')[1].split(']')[0])
            for k in f.keys() if k.startswith('cardio[') and '[machine]' in k
        ))
        has_cardio = len(cardio_indices) > 0
        for j in cardio_indices:
            machine = f[f'cardio[{j}][machine]']
            # outdoor_bike uses distance_km; others use distance_m
            dist_m = None
            if f.get(f'cardio[{j}][distance_m]'):
                dist_m = int(float(f[f'cardio[{j}][distance_m]']))
            elif f.get(f'cardio[{j}][distance_km]'):
                dist_m = int(float(f[f'cardio[{j}][distance_km]']) * 1000)
            db.session.add(CardioSet(
                workout_id   = workout.id,
                machine      = machine,
                set_number   = j + 1,
                distance_m   = dist_m,
                duration_s   = _time_to_seconds(f.get(f'cardio[{j}][duration]')),
                calories     = int(f[f'cardio[{j}][calories]'])   if f.get(f'cardio[{j}][calories]')   else None,
                damper       = int(f[f'cardio[{j}][damper]'])     if f.get(f'cardio[{j}][damper]')     else None,
                rpe          = float(f[f'cardio[{j}][rpe]']) if f.get(f'cardio[{j}][rpe]') else None,
            ))

        # Dual tag: if strength + cardio, mark as strength+cardio
        if has_cardio and len(set_indices) > 0:
            workout.workout_type = 'strength+cardio'

        db.session.commit()

        # Auto-link to program day if started from program
        program_day_id = f.get('program_day_id')
        if program_day_id:
            from ..models import ProgramCompletion, ProgramDay
            day  = ProgramDay.query.get(int(program_day_id))
            if day:
                comp = ProgramCompletion.query.filter_by(day_id=day.id).first()
                if not comp:
                    comp = ProgramCompletion(day_id=day.id)
                    db.session.add(comp)
                comp.workout_id = workout.id
                comp.completed  = True
                comp.status     = 'done'
                comp.done_date  = workout.completed_at.date()
                db.session.commit()
                return _htmx_or_redirect(url_for('program.week',
                    program_id=day.program_id, week_num=day.week_number))

        return _htmx_or_redirect(url_for('workouts.view', workout_id=workout.id))

    return render_template('workouts/log_strength.html', exercises=exercises,
                           locations=LOCATION_CHOICES)


@workouts_bp.route('/htmx/set-row')
def htmx_set_row():
    index     = request.args.get('index', 0, type=int)
    exercises = Exercise.query.order_by(Exercise.name).all()
    return render_template('partials/set_row.html', index=index, exercises=exercises)


# ── Log Cardio (selection hub) ──────────────────────────────
@workouts_bp.route('/log/cardio')
def log_cardio():
    return render_template('workouts/log_cardio_select.html')


# ── Log Cardio Machine (standalone: row, skierg, stairclimber, other) ──
@workouts_bp.route('/log/cardio/machine', methods=['GET', 'POST'])
def log_cardio_machine():
    if request.method == 'GET':
        machine = request.args.get('machine', 'row')
        return render_template('workouts/log_cardio_machine.html',
                               machine=machine, locations=LOCATION_CHOICES)

    f = request.form
    workout = Workout(
        workout_type='cardio',
        name=f.get('name') or 'Cardio Session',
        location=f.get('location', 'gym'),
        duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,
        notes=f.get('notes'),
        completed_at=datetime.fromisoformat(f['completed_at']) if f.get('completed_at') else datetime.utcnow()
    )
    db.session.add(workout)
    db.session.flush()

    cardio_indices = sorted(set(
        int(k.split('[')[1].split(']')[0])
        for k in f.keys() if k.startswith('cardio[') and '[machine]' in k
    ))
    for j in cardio_indices:
        db.session.add(CardioSet(
            workout_id = workout.id,
            machine    = f[f'cardio[{j}][machine]'],
            set_number = j + 1,
            distance_m = (lambda raw, unit: int(round(float(raw) * (1609.344 if unit == 'mi' else 1))) if raw else None)(
                f.get(f'cardio[{j}][distance_m]'), f.get(f'cardio[{j}][distance_unit]', 'm')),
            duration_s = _time_to_seconds(f.get(f'cardio[{j}][duration]')),
            calories   = int(f[f'cardio[{j}][calories]'])  if f.get(f'cardio[{j}][calories]')  else None,
            damper     = int(f[f'cardio[{j}][damper]'])    if f.get(f'cardio[{j}][damper]')    else None,
            rpe        = float(f[f'cardio[{j}][rpe]'])     if f.get(f'cardio[{j}][rpe]')       else None,
        ))
    db.session.commit()
    return _htmx_or_redirect(url_for('workouts.view', workout_id=workout.id))


# ── Log Run ────────────────────────────────────────────────
@workouts_bp.route('/log/run', methods=['GET', 'POST'])
def log_run():
    if request.method == 'POST':
        f = request.form
        workout = Workout(
            workout_type='run',
            name=f.get('name', 'Run'),
            location=f.get('location', 'gym'),
            duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,
            calories=int(f['calories']) if f.get('calories') else None,
            avg_bpm=int(f['avg_bpm']) if f.get('avg_bpm') else None,
            notes=f.get('notes'),
            completed_at=datetime.fromisoformat(f['completed_at']) if f.get('completed_at') else datetime.utcnow()
        )
        db.session.add(workout)
        db.session.flush()

        dist_raw  = f.get('total_distance_km')
        dist_unit = f.get('distance_unit', 'km')
        total_dist_km = None
        if dist_raw:
            total_dist_km = float(dist_raw)
            if dist_unit == 'mi':
                total_dist_km = total_dist_km * 1.60934

        run = Run(
            workout_id        = workout.id,
            run_type          = f.get('run_type', 'continuous'),
            total_distance_km = total_dist_km,
            total_duration_s  = _time_to_seconds(f.get('total_duration')),
            avg_heart_rate    = int(f['avg_heart_rate']) if f.get('avg_heart_rate') else None,
            route_notes       = f.get('route_notes'),
        )
        db.session.add(run)
        db.session.flush()

        # Warmup
        if f.get('warmup_distance') or f.get('warmup_duration'):
            db.session.add(RunSegment(
                run_id         = run.id,
                segment_type   = 'warmup',
                segment_number = 1,
                distance_km    = float(f['warmup_distance']) if f.get('warmup_distance') else None,
                duration_s     = _time_to_seconds(f.get('warmup_duration')),
                avg_bpm        = int(f['warmup_bpm']) if f.get('warmup_bpm') else None,
            ))

        # Intervals
        i = 0
        while f.get(f'intervals[{i}][distance_km]') or f.get(f'intervals[{i}][duration]'):
            db.session.add(RunSegment(
                run_id         = run.id,
                segment_type   = 'interval',
                segment_number = i + 1,
                distance_km    = float(f[f'intervals[{i}][distance_km]']) if f.get(f'intervals[{i}][distance_km]') else None,
                duration_s     = _time_to_seconds(f.get(f'intervals[{i}][duration]')),
                skipped        = bool(f.get(f'intervals[{i}][skipped]')),
                notes          = f.get(f'intervals[{i}][notes]'),
            ))
            i += 1

        # Cooldown
        if f.get('cooldown_distance') or f.get('cooldown_duration'):
            db.session.add(RunSegment(
                run_id         = run.id,
                segment_type   = 'cooldown',
                segment_number = 1,
                distance_km    = float(f['cooldown_distance']) if f.get('cooldown_distance') else None,
                duration_s     = _time_to_seconds(f.get('cooldown_duration')),
            ))

        db.session.commit()
        return _htmx_or_redirect(url_for('workouts.view', workout_id=workout.id))

    return render_template('workouts/log_run.html', locations=LOCATION_CHOICES)


# ── Log Bike ────────────────────────────────────────────────
@workouts_bp.route('/log/bike', methods=['GET', 'POST'])
def log_bike():
    if request.method == 'POST':
        f = request.form
        dist_raw  = f.get('total_distance_km')
        dist_unit = f.get('distance_unit', 'km')
        total_distance_km = None
        if dist_raw:
            total_distance_km = float(dist_raw)
            if dist_unit == 'mi':
                total_distance_km = total_distance_km * 1.60934

        workout = Workout(
            workout_type='bike',
            name=f.get('name') or 'Bike Ride',
            location=f.get('location', 'gym'),
            duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,
            calories=int(f['calories']) if f.get('calories') else None,
            avg_bpm=int(f['avg_heart_rate']) if f.get('avg_heart_rate') else None,
            notes=f.get('notes'),
            completed_at=datetime.fromisoformat(f['completed_at']) if f.get('completed_at') else datetime.utcnow()
        )
        db.session.add(workout)
        db.session.flush()

        run = Run(
            workout_id        = workout.id,
            run_type          = f.get('run_type', 'continuous'),
            total_distance_km = total_distance_km,
            total_duration_s  = _time_to_seconds(f.get('total_duration')),
            avg_heart_rate    = int(f['avg_heart_rate']) if f.get('avg_heart_rate') else None,
            route_notes       = f.get('route_notes'),
        )
        db.session.add(run)
        db.session.commit()
        return _htmx_or_redirect(url_for('workouts.view', workout_id=workout.id))

    environment = request.args.get('environment', 'indoor')
    return render_template('workouts/log_bike.html',
                           environment=environment,
                           locations=LOCATION_CHOICES)


@workouts_bp.route('/htmx/interval-row')
def htmx_interval_row():
    index = request.args.get('index', 0, type=int)
    return render_template('partials/interval_row.html', index=index)


# ── Log Mobility ────────────────────────────────────────────
@workouts_bp.route('/log/mobility', methods=['GET', 'POST'])
def log_mobility():
    if request.method == 'POST':
        f = request.form
        notes_parts = []
        if f.get('mobility_type'):
            type_labels = {
                'yoga': 'Yoga', 'mobility_flow': 'Mobility Flow',
                'foam_rolling': 'Foam Rolling', 'stretching': 'Stretching',
                'mixed': 'Mixed', 'other': 'Other',
            }
            notes_parts.append('Type: ' + type_labels.get(f['mobility_type'], f['mobility_type']))
        if f.get('focus_areas'):
            notes_parts.append('Focus: ' + f['focus_areas'])
        # Collect exercises list
        ex_lines = []
        i = 0
        while f.get(f'exercises[{i}][name]') is not None:
            ex_name = f.get(f'exercises[{i}][name]', '').strip()
            ex_dur  = f.get(f'exercises[{i}][duration]', '').strip()
            if ex_name:
                ex_lines.append(f'  - {ex_name}' + (f' ({ex_dur})' if ex_dur else ''))
            i += 1
        if ex_lines:
            notes_parts.append('Exercises:\n' + '\n'.join(ex_lines))
        if f.get('notes'):
            notes_parts.append(f['notes'])
        combined_notes = '\n'.join(notes_parts) or None

        workout = Workout(
            workout_type='mobility',
            name=f.get('name') or 'Mobility Session',
            location=f.get('location', 'home'),
            duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,
            notes=combined_notes,
            completed_at=datetime.fromisoformat(f['completed_at']) if f.get('completed_at') else datetime.utcnow()
        )
        db.session.add(workout)
        db.session.commit()
        return _htmx_or_redirect(url_for('workouts.view', workout_id=workout.id))
    exercises = Exercise.query.order_by(Exercise.name).all()
    return render_template('workouts/log_mobility.html', locations=LOCATION_CHOICES, exercises=exercises)


# ── Hyrox Start (selection page) ───────────────────────────
@workouts_bp.route('/log/hyrox')
def log_hyrox():
    return render_template('workouts/hyrox_select.html',
                           training_presets=HYROX_TRAINING_PRESETS)


# ── Log Hyrox Race ─────────────────────────────────────────
@workouts_bp.route('/log/hyrox/race', methods=['GET', 'POST'])
def log_hyrox_race():
    if request.method == 'POST':
        f = request.form
        workout = Workout(
            workout_type='hyrox',
            name=f.get('name', 'Hyrox'),
            location='gym',
            duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,
            calories=int(f['calories']) if f.get('calories') else None,
            avg_bpm=int(f['avg_bpm']) if f.get('avg_bpm') else None,
            notes=f.get('notes'),
            completed_at=datetime.fromisoformat(f['completed_at']) if f.get('completed_at') else datetime.utcnow()
        )
        db.session.add(workout)
        db.session.flush()

        result = HyroxResult(
            workout_id     = workout.id,
            total_time_s   = _time_to_seconds(f.get('total_time')),
            running_time_s = _time_to_seconds(f.get('running_time')),
            workout_time_s = _time_to_seconds(f.get('workout_time')),
            location       = f.get('venue'),
            race_type      = f.get('race_type', 'singles'),
        )
        db.session.add(result)
        db.session.flush()

        _save_hyrox_stations(result.id, f)
        db.session.commit()
        return _htmx_or_redirect(url_for('workouts.view', workout_id=workout.id))

    race_type = request.args.get('race_type', 'singles')
    return render_template('workouts/log_hyrox.html',
                           session_mode='race',
                           race_type=race_type,
                           default_stations=HYROX_DEFAULT_STATIONS,
                           locations=LOCATION_CHOICES)


# ── Log Hyrox Training ─────────────────────────────────────
@workouts_bp.route('/log/hyrox/training', methods=['GET', 'POST'])
def log_hyrox_training():
    template_id = request.args.get('template_id', type=int)
    preset_key  = request.args.get('preset', 'full_sim')

    if template_id:
        from ..models import WorkoutTemplate
        import json as _json
        tmpl = WorkoutTemplate.query.get(template_id)
        if tmpl and tmpl.workout_type == 'hyrox':
            try:
                tdata = _json.loads(tmpl.template_data) if tmpl.template_data else {}
            except Exception:
                tdata = {}
            raw_stations = tdata.get('stations', [])
            stations = [
                (s.get('name', ''), i + 1, s.get('distance_m'), s.get('reps'))
                for i, s in enumerate(raw_stations)
            ]
            preset = {'label': tmpl.name, 'default_name': tmpl.name, 'stations': stations}
        else:
            template_id = None
            preset = HYROX_TRAINING_PRESETS.get(preset_key, HYROX_TRAINING_PRESETS['full_sim'])
    else:
        preset = HYROX_TRAINING_PRESETS.get(preset_key, HYROX_TRAINING_PRESETS['full_sim'])

    if request.method == 'POST':
        f = request.form
        workout = Workout(
            workout_type='hyrox',
            name=f.get('name', preset['default_name']),
            location='gym',
            duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,
            calories=int(f['calories']) if f.get('calories') else None,
            avg_bpm=int(f['avg_bpm']) if f.get('avg_bpm') else None,
            notes=f.get('notes'),
            completed_at=datetime.fromisoformat(f['completed_at']) if f.get('completed_at') else datetime.utcnow()
        )
        db.session.add(workout)
        db.session.flush()

        result = HyroxResult(
            workout_id     = workout.id,
            total_time_s   = _time_to_seconds(f.get('total_time')),
            running_time_s = _time_to_seconds(f.get('running_time')),
            workout_time_s = _time_to_seconds(f.get('workout_time')),
            location       = f.get('venue'),
            race_type      = f'training_template_{template_id}' if template_id else f'training_{preset_key}',
        )
        db.session.add(result)
        db.session.flush()

        _save_hyrox_stations(result.id, f)
        db.session.commit()

        program_day_id = f.get('program_day_id')
        if program_day_id:
            from ..models import ProgramCompletion, ProgramDay
            day = ProgramDay.query.get(int(program_day_id))
            if day:
                comp = ProgramCompletion.query.filter_by(day_id=day.id).first()
                if not comp:
                    comp = ProgramCompletion(day_id=day.id)
                    db.session.add(comp)
                comp.workout_id = workout.id
                comp.completed  = True
                comp.status     = 'done'
                comp.done_date  = workout.completed_at.date()
                db.session.commit()
                return _htmx_or_redirect(url_for('program.week',
                    program_id=day.program_id, week_num=day.week_number))

        return _htmx_or_redirect(url_for('workouts.view', workout_id=workout.id))

    program_day_id = request.args.get('program_day_id')
    return render_template('workouts/log_hyrox.html',
                           session_mode='training',
                           preset=preset,
                           default_stations=preset['stations'],
                           locations=LOCATION_CHOICES,
                           program_day_id=program_day_id,
                           weight_unit=session.get('weight_unit', 'lbs'))


# ── Circuit hub (selection page) ────────────────────────────
@workouts_bp.route('/log/circuit/hub')
def log_circuit_hub():
    return render_template('workouts/log_circuit_select.html')


# ── Log Circuit / AMRAP / EMOM / For Time ──────────────────
@workouts_bp.route('/log/circuit', methods=['GET', 'POST'])
def log_circuit():
    exercises    = Exercise.query.order_by(Exercise.name).all()
    circuit_type = request.args.get('type', 'circuit')

    if request.method == 'POST':
        f            = request.form
        circuit_type = f.get('circuit_type', 'circuit')
        workout = Workout(
            workout_type=circuit_type,
            name=f.get('name', f'{circuit_type.upper()} Session'),
            location=f.get('location', 'gym'),
            duration_minutes=int(f['duration_minutes']) if f.get('duration_minutes') else None,
            calories=int(f['calories']) if f.get('calories') else None,
            avg_bpm=int(f['avg_bpm']) if f.get('avg_bpm') else None,
            notes=f.get('notes'),
            completed_at=datetime.fromisoformat(f['completed_at']) if f.get('completed_at') else datetime.utcnow()
        )
        db.session.add(workout)
        db.session.flush()

        circuit = Circuit(
            workout_id       = workout.id,
            circuit_type     = circuit_type,
            rounds_target    = int(f['rounds_target']) if f.get('rounds_target') else None,
            rounds_completed = float(f['rounds_completed']) if f.get('rounds_completed') else None,
            time_cap_s       = _time_to_seconds(f.get('time_cap')),
            total_time_s     = _time_to_seconds(f.get('total_time')),
            notes            = f.get('circuit_notes'),
        )
        db.session.add(circuit)
        db.session.flush()

        # Parse For Time round splits (MM:SS → seconds)
        splits = []
        k = 0
        while f.get(f'round_splits[{k}]') is not None:
            splits.append(_time_to_seconds(f.get(f'round_splits[{k}]')))
            k += 1
        if splits:
            circuit.round_splits = splits

        i = 0
        while f.get(f'exercises[{i}][exercise_id]'):
            # Derive target reps/distance from first round
            first_reps = int(f[f'exercises[{i}][rounds][0][reps]']) if f.get(f'exercises[{i}][rounds][0][reps]') else None
            first_dist = int(f[f'exercises[{i}][rounds][0][distance_m]']) if f.get(f'exercises[{i}][rounds][0][distance_m]') else None
            # Fall back to flat fields for manual (non-template) log forms
            target_reps = first_reps if first_reps is not None else (int(f[f'exercises[{i}][reps]']) if f.get(f'exercises[{i}][reps]') else None)
            target_dist = first_dist if first_dist is not None else (int(f[f'exercises[{i}][distance_m]']) if f.get(f'exercises[{i}][distance_m]') else None)

            # Derive target weight from first round's weight field
            first_wt_raw = f.get(f'exercises[{i}][rounds][0][weight]', '').strip()
            target_wt_lbs = float(first_wt_raw) if first_wt_raw else None

            ce = CircuitExercise(
                circuit_id        = circuit.id,
                exercise_id       = int(f[f'exercises[{i}][exercise_id]']),
                order_index       = i,
                target_reps       = target_reps,
                target_weight_lbs = target_wt_lbs,
                target_distance_m = target_dist,
                notes             = f.get(f'exercises[{i}][notes]'),
            )
            db.session.add(ce)
            db.session.flush()

            # Create per-round sets with reps/distance and weight
            j = 0
            while f.get(f'exercises[{i}][rounds][{j}][reps]') is not None or f.get(f'exercises[{i}][rounds][{j}][distance_m]') is not None:
                reps_val = f.get(f'exercises[{i}][rounds][{j}][reps]', '').strip()
                dist_val = f.get(f'exercises[{i}][rounds][{j}][distance_m]', '').strip()
                wt_raw = f.get(f'exercises[{i}][rounds][{j}][weight]', '').strip()
                wt_lbs = wt_kg = None
                if wt_raw:
                    wt_lbs = float(wt_raw)
                    wt_kg  = lbs_to_kg(wt_lbs)
                rs = CircuitRoundSet(
                    circuit_exercise_id = ce.id,
                    round_number        = j + 1,
                    reps                = int(reps_val) if reps_val.isdigit() else None,
                    distance_m          = float(dist_val) if dist_val else None,
                    weight_lbs          = wt_lbs,
                    weight_kg           = wt_kg,
                )
                db.session.add(rs)
                j += 1

            i += 1

        db.session.commit()
        return _htmx_or_redirect(url_for('workouts.view', workout_id=workout.id))

    return render_template('workouts/log_circuit.html', exercises=exercises,
                           circuit_type=circuit_type, locations=LOCATION_CHOICES)


@workouts_bp.route('/htmx/circuit-exercise-row')
def htmx_circuit_exercise_row():
    index     = request.args.get('index', 0, type=int)
    exercises = Exercise.query.order_by(Exercise.name).all()
    return render_template('partials/circuit_exercise_row.html', index=index, exercises=exercises)




# ── CSV Export ─────────────────────────────────────────────
@workouts_bp.route('/export/csv')
def export_csv():
    workouts = Workout.query.order_by(Workout.completed_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # ── Workouts sheet ──────────────────────────────────────
    writer.writerow(['=== WORKOUTS ==='])
    writer.writerow(['id','date','name','type','location','duration_min','calories','avg_bpm','notes'])
    for w in workouts:
        writer.writerow([
            w.id,
            w.completed_at.strftime('%Y-%m-%d %H:%M'),
            w.name, w.workout_type, w.location or '',
            w.duration_minutes or '', w.calories or '',
            w.avg_bpm or '', w.notes or '',
        ])

    writer.writerow([])

    # ── Strength sets ───────────────────────────────────────
    writer.writerow(['=== STRENGTH SETS ==='])
    writer.writerow(['workout_id','date','workout_name','exercise','set_num','weight_lbs','weight_kg','reps','rpe','notes'])
    sets = (db.session.query(WorkoutSet)
            .join(Workout).order_by(Workout.completed_at.desc(), WorkoutSet.set_number).all())
    for s in sets:
        writer.writerow([
            s.workout_id,
            s.workout.completed_at.strftime('%Y-%m-%d'),
            s.workout.name,
            s.exercise.name,
            s.set_number,
            float(s.weight_lbs) if s.weight_lbs else '',
            float(s.weight_kg)  if s.weight_kg  else '',
            s.reps or '', float(s.rpe) if s.rpe else '',
            s.notes or '',
        ])

    writer.writerow([])

    # ── Runs ────────────────────────────────────────────────
    writer.writerow(['=== RUNS ==='])
    writer.writerow(['workout_id','date','workout_name','type','distance_km','duration_s','avg_hr'])
    runs = (db.session.query(Run).join(Workout)
            .order_by(Workout.completed_at.desc()).all())
    for r in runs:
        writer.writerow([
            r.workout_id,
            r.workout.completed_at.strftime('%Y-%m-%d'),
            r.workout.name, r.run_type,
            float(r.total_distance_km) if r.total_distance_km else '',
            r.total_duration_s or '',
            r.avg_heart_rate or '',
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=forge_export.csv'}
    )

# ── Helpers ────────────────────────────────────────────────
def _save_hyrox_stations(result_id, f):
    i = 0
    while f.get(f'stations[{i}][name]'):
        if f.get(f'stations[{i}][skipped]'):
            i += 1
            continue

        weight_raw = float(f[f'stations[{i}][weight]']) if f.get(f'stations[{i}][weight]') else None
        unit = f.get(f'stations[{i}][unit]', 'lbs')
        weight_kg = weight_lbs = None
        if weight_raw:
            if unit == 'lbs':
                weight_lbs = weight_raw
                weight_kg  = lbs_to_kg(weight_raw)
            else:
                weight_kg  = weight_raw
                weight_lbs = weight_raw * 2.20462

        had_break        = bool(f.get(f'stations[{i}][had_break]'))
        is_substituted   = bool(f.get(f'stations[{i}][is_substituted]'))
        sub_name         = f.get(f'stations[{i}][sub_exercise_name]') or None

        station = HyroxStation(
            hyrox_result_id   = result_id,
            station_order     = i + 1,
            station_name      = f[f'stations[{i}][name]'],
            time_s            = _time_to_seconds(f.get(f'stations[{i}][time]')),
            weight_kg         = weight_kg,
            weight_lbs        = weight_lbs,
            distance_m        = int(f[f'stations[{i}][distance_m]']) if f.get(f'stations[{i}][distance_m]') else None,
            reps              = int(f[f'stations[{i}][reps]'])       if f.get(f'stations[{i}][reps]')       else None,
            damper            = int(f[f'stations[{i}][damper]'])     if f.get(f'stations[{i}][damper]')     else None,
            rest_after_s      = _time_to_seconds(f.get(f'stations[{i}][rest_after]')),
            notes             = f.get(f'stations[{i}][notes]'),
            had_break         = had_break,
            is_substituted    = is_substituted,
            sub_exercise_name = sub_name,
        )
        db.session.add(station)
        db.session.flush()  # populate station.id before inserting segments

        if had_break:
            # Collect all segment indices that have any data (handles gaps from deleted segments)
            seg_indices = sorted(set(
                int(k.split(f'stations[{i}][segments][')[1].split(']')[0])
                for k in f.keys()
                if f'stations[{i}][segments][' in k
            ))
            for j in seg_indices:
                seg_w_raw = float(f[f'stations[{i}][segments][{j}][weight]']) \
                    if f.get(f'stations[{i}][segments][{j}][weight]') else None
                seg_unit = f.get(f'stations[{i}][segments][{j}][unit]', unit)
                seg_wkg = seg_wlbs = None
                if seg_w_raw:
                    if seg_unit == 'lbs':
                        seg_wlbs = seg_w_raw
                        seg_wkg  = lbs_to_kg(seg_w_raw)
                    else:
                        seg_wkg  = seg_w_raw
                        seg_wlbs = seg_w_raw * 2.20462

                db.session.add(HyroxStationSegment(
                    hyrox_station_id = station.id,
                    segment_order    = j + 1,
                    distance_m       = int(f[f'stations[{i}][segments][{j}][distance_m]'])
                                       if f.get(f'stations[{i}][segments][{j}][distance_m]') else None,
                    reps             = int(f[f'stations[{i}][segments][{j}][reps]'])
                                       if f.get(f'stations[{i}][segments][{j}][reps]') else None,
                    weight_kg        = seg_wkg,
                    weight_lbs       = seg_wlbs,
                    time_s           = _time_to_seconds(f.get(f'stations[{i}][segments][{j}][time]')),
                    notes            = f.get(f'stations[{i}][segments][{j}][notes]'),
                ))
        i += 1


def _time_to_seconds(t):
    """Parse MM:SS or HH:MM:SS to seconds."""
    if not t or not t.strip():
        return None
    parts = t.strip().split(':')
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        return None


# ── Edit Workout ───────────────────────────────────────────
@workouts_bp.route('/<int:workout_id>/edit', methods=['GET', 'POST'])
def edit(workout_id):
    workout   = Workout.query.get_or_404(workout_id)
    exercises = Exercise.query.order_by(Exercise.name).all()
    wtype     = workout.workout_type

    if request.method == 'POST':
        f = request.form

        # ── Update base workout fields ──────────────────────
        workout.name             = f.get('name', workout.name)
        workout.location         = f.get('location', workout.location)
        workout.duration_minutes = int(f['duration_minutes']) if f.get('duration_minutes') else None
        workout.calories         = int(f['calories'])         if f.get('calories')         else None
        workout.avg_bpm          = int(f['avg_bpm'])          if f.get('avg_bpm')          else None
        workout.session_rpe      = float(f['session_rpe'])    if f.get('session_rpe')      else None
        workout.notes            = f.get('notes')
        if f.get('completed_at'):
            workout.completed_at = datetime.fromisoformat(f['completed_at'])

        # ── Strength / Strength+Cardio ──────────────────────
        if wtype in ('strength', 'strength+cardio'):
            # Delete existing sets and re-insert (non-contiguous index safe)
            WorkoutSet.query.filter_by(workout_id=workout.id).delete()
            set_indices = sorted(set(
                int(k.split('[')[1].split(']')[0])
                for k in f.keys() if k.startswith('sets[') and '[exercise_id]' in k
            ))
            for i in set_indices:
                ex_id = f.get(f'sets[{i}][exercise_id]')
                if not ex_id:
                    continue
                weight_raw = f.get(f'sets[{i}][weight]') or None
                unit       = f.get(f'sets[{i}][unit]', 'lbs')
                weight_kg = weight_lbs = None
                if weight_raw:
                    w = float(weight_raw)
                    if unit == 'lbs':
                        weight_lbs = w; weight_kg = lbs_to_kg(w)
                    else:
                        weight_kg = w; weight_lbs = w * 2.20462
                db.session.add(WorkoutSet(
                    workout_id  = workout.id,
                    exercise_id = int(ex_id),
                    set_number  = int(f.get(f'sets[{i}][set_number]', i + 1)),
                    weight_kg   = weight_kg,
                    weight_lbs  = weight_lbs,
                    reps        = int(f[f'sets[{i}][reps]'])   if f.get(f'sets[{i}][reps]')   else None,
                    rpe         = float(f[f'sets[{i}][rpe]'])  if f.get(f'sets[{i}][rpe]')    else None,
                    notes       = f.get(f'sets[{i}][notes]'),
                ))

            # Re-save cardio sets
            CardioSet.query.filter_by(workout_id=workout.id).delete()
            cardio_indices = sorted(set(
                int(k.split('[')[1].split(']')[0])
                for k in f.keys() if k.startswith('cardio[') and '[machine]' in k
            ))
            has_cardio = len(cardio_indices) > 0
            for j in cardio_indices:
                machine = f[f'cardio[{j}][machine]']
                dist_m = None
                if f.get(f'cardio[{j}][distance_m]'):
                    raw = float(f[f'cardio[{j}][distance_m]'])
                    unit = f.get(f'cardio[{j}][distance_unit]', 'm')
                    dist_m = int(round(raw * (1609.344 if unit == 'mi' else 1)))
                elif f.get(f'cardio[{j}][distance_km]'):
                    dist_m = int(float(f[f'cardio[{j}][distance_km]']) * 1000)
                db.session.add(CardioSet(
                    workout_id   = workout.id,
                    machine      = machine,
                    set_number   = j + 1,
                    distance_m   = dist_m,
                    duration_s   = _time_to_seconds(f.get(f'cardio[{j}][duration]')),
                    calories     = int(f[f'cardio[{j}][calories]'])   if f.get(f'cardio[{j}][calories]')   else None,
                    damper       = int(f[f'cardio[{j}][damper]'])     if f.get(f'cardio[{j}][damper]')     else None,
                    rpe          = float(f[f'cardio[{j}][rpe]']) if f.get(f'cardio[{j}][rpe]') else None,
                ))
            # Update workout type
            if has_cardio and len(set_indices) > 0:
                workout.workout_type = 'strength+cardio'
            elif len(set_indices) > 0:
                workout.workout_type = 'strength'

        # ── Circuit / AMRAP ─────────────────────────────────
        elif wtype in ('circuit', 'amrap'):
            circuit = workout.circuits.first()
            if circuit:
                circuit.rounds_completed = float(f['rounds_completed']) if f.get('rounds_completed') else None
                circuit.rounds_target    = int(f['rounds_target'])      if f.get('rounds_target')    else None
                circuit.total_time_s     = _time_to_seconds(f.get('total_time'))
                circuit.time_cap_s       = _time_to_seconds(f.get('time_cap'))
                circuit.notes            = f.get('circuit_notes')

                # Update per-exercise round sets
                for ce in circuit.exercises.all():
                    # Delete existing round sets for this exercise
                    CircuitRoundSet.query.filter_by(circuit_exercise_id=ce.id).delete()
                    r = 1
                    while f.get(f'ce[{ce.id}][round][{r}][reps]') is not None or \
                          f.get(f'ce[{ce.id}][round][{r}][duration]') is not None or \
                          f.get(f'ce[{ce.id}][round][{r}][weight]') is not None:
                        reps_val = f.get(f'ce[{ce.id}][round][{r}][reps]')
                        dur_val  = f.get(f'ce[{ce.id}][round][{r}][duration]')
                        w_val    = f.get(f'ce[{ce.id}][round][{r}][weight]')
                        if reps_val or dur_val or w_val:
                            w = float(w_val) if w_val else None
                            db.session.add(CircuitRoundSet(
                                circuit_exercise_id = ce.id,
                                round_number        = r,
                                reps       = int(reps_val) if reps_val else None,
                                duration_s = _time_to_seconds(dur_val),
                                weight_lbs = w,
                                weight_kg  = lbs_to_kg(w) if w else None,
                            ))
                        r += 1

        # ── Run ─────────────────────────────────────────────
        elif wtype == 'run':
            run = workout.runs.first()
            if run:
                run.total_distance_km = float(f['total_distance_km']) if f.get('total_distance_km') else None
                run.total_duration_s  = _time_to_seconds(f.get('total_duration'))
                run.route_notes       = f.get('route_notes')
                # Update segments
                RunSegment.query.filter_by(run_id=run.id).delete()
                i = 0
                while f.get(f'segs[{i}][type]'):
                    db.session.add(RunSegment(
                        run_id         = run.id,
                        segment_type   = f[f'segs[{i}][type]'],
                        segment_number = int(f.get(f'segs[{i}][num]', i)),
                        distance_km    = float(f[f'segs[{i}][dist]']) if f.get(f'segs[{i}][dist]') else None,
                        duration_s     = _time_to_seconds(f.get(f'segs[{i}][dur]')),
                        skipped        = bool(f.get(f'segs[{i}][skipped]')),
                    ))
                    i += 1

        db.session.commit()
        return _htmx_or_redirect(url_for('workouts.view', workout_id=workout.id))

    # GET — render edit form
    return render_template('workouts/edit.html', workout=workout, exercises=exercises,
                           locations=LOCATION_CHOICES)


# ── Exercise history + PR (HTMX) ───────────────────────────
@workouts_bp.route('/htmx/exercise-history')
def htmx_exercise_history():
    ex_id = request.args.get('exercise_id', type=int)
    if not ex_id:
        return ('', 204)

    # Last session that used this exercise
    last_set = (
        db.session.query(WorkoutSet)
        .join(Workout)
        .filter(WorkoutSet.exercise_id == ex_id, WorkoutSet.skipped == False)
        .order_by(Workout.completed_at.desc())
        .first()
    )
    if not last_set:
        return render_template('partials/exercise_history.html',
                               last_sets=[], pr_lbs=None, last_date=None)

    last_workout_id = last_set.workout_id
    last_date       = last_set.workout.completed_at

    last_sets = (
        db.session.query(WorkoutSet)
        .filter(WorkoutSet.workout_id == last_workout_id,
                WorkoutSet.exercise_id == ex_id,
                WorkoutSet.skipped == False)
        .order_by(WorkoutSet.set_number)
        .all()
    )

    pr_lbs = db.session.query(func.max(WorkoutSet.weight_lbs)) \
        .filter(WorkoutSet.exercise_id == ex_id,
                WorkoutSet.skipped == False) \
        .scalar()

    # ── Personal best (best estimated 1RM via Epley) ──────
    all_sets = (
        db.session.query(WorkoutSet)
        .filter(WorkoutSet.exercise_id == ex_id, WorkoutSet.skipped == False,
                WorkoutSet.weight_lbs.isnot(None), WorkoutSet.reps.isnot(None))
        .all()
    )
    best_set = None
    best_1rm = 0.0
    for s in all_sets:
        r = s.reps or 1
        est = float(s.weight_lbs) * (1 + r / 30.0)
        if est > best_1rm:
            best_1rm = est
            best_set = s

    # ── Recent sessions (last 5 unique workouts) ──────────
    recent_workout_ids = (
        db.session.query(WorkoutSet.workout_id)
        .join(Workout)
        .filter(WorkoutSet.exercise_id == ex_id, WorkoutSet.skipped == False)
        .group_by(WorkoutSet.workout_id, Workout.completed_at)
        .order_by(Workout.completed_at.desc())
        .limit(5)
        .all()
    )
    recent_sessions = []
    for (wid,) in recent_workout_ids:
        w = Workout.query.get(wid)
        top = (
            db.session.query(WorkoutSet)
            .filter(WorkoutSet.workout_id == wid, WorkoutSet.exercise_id == ex_id,
                    WorkoutSet.skipped == False)
            .order_by(WorkoutSet.weight_lbs.desc().nullslast(), WorkoutSet.reps.desc().nullslast())
            .first()
        )
        if top:
            recent_sessions.append({'date': w.completed_at, 'set': top})

    return render_template('partials/exercise_history.html',
                           last_sets=last_sets,
                           pr_lbs=float(pr_lbs) if pr_lbs else None,
                           last_date=last_date,
                           best_set=best_set,
                           best_1rm=round(best_1rm) if best_1rm else None,
                           recent_sessions=recent_sessions)