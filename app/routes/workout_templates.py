from flask import Blueprint, render_template, request, redirect, url_for, session
from ..models import db, WorkoutTemplate, Exercise
from ..utils import clean_exercise_name, fuzzy_match
import json

def _all_exercises():
    return Exercise.query.order_by(Exercise.name).all()

workout_templates_bp = Blueprint('workout_templates', __name__)

HYROX_PRESET_LABELS = {
    'full_sim':      'Full Sim (16 stations)',
    'half_sim_a':    'Half Sim A (stations 1–8)',
    'half_sim_b':    'Half Sim B (stations 9–16)',
    'workouts_only': 'Workouts Only (no running)',
    'running_only':  'Running Only (8 × 1 km)',
}

HYROX_PRESET_STATIONS = {
    'full_sim': [
        '1km Run', 'SkiErg (1000m)', '1km Run', 'Sled Push (50m)',
        '1km Run', 'Sled Pull (50m)', '1km Run', 'Burpee Broad Jump (80 reps)',
        '1km Run', 'Row (1000m)', '1km Run', 'Farmers Carry (200m)',
        '1km Run', 'Sandbag Lunges (100 reps)', '1km Run', 'Wall Balls (100 reps)',
    ],
    'half_sim_a': [
        '1km Run', 'SkiErg (1000m)', '1km Run', 'Sled Push (50m)',
        '1km Run', 'Sled Pull (50m)', '1km Run', 'Burpee Broad Jump (80 reps)',
    ],
    'half_sim_b': [
        '1km Run', 'Row (1000m)', '1km Run', 'Farmers Carry (200m)',
        '1km Run', 'Sandbag Lunges (100 reps)', '1km Run', 'Wall Balls (100 reps)',
    ],
    'workouts_only': [
        'SkiErg (1000m)', 'Sled Push (50m)', 'Sled Pull (50m)',
        'Burpee Broad Jump (80 reps)', 'Row (1000m)', 'Farmers Carry (200m)',
        'Sandbag Lunges (100 reps)', 'Wall Balls (100 reps)',
    ],
    'running_only': [
        '1km Run', '1km Run', '1km Run', '1km Run',
        '1km Run', '1km Run', '1km Run', '1km Run',
    ],
}


# ── Type picker ────────────────────────────────────────────────────────────────

@workout_templates_bp.route('/new')
def new_picker():
    return render_template('workout_templates/type_picker.html')


# ── Strength template ──────────────────────────────────────────────────────────

@workout_templates_bp.route('/new/strength', methods=['GET', 'POST'])
def new_strength():
    if request.method == 'POST':
        f = request.form
        exercises_out = []
        i = 0
        while f.get(f'exercises[{i}][exercise_name]') is not None or f.get(f'exercises[{i}][exercise_id]') is not None:
            ex_name = f.get(f'exercises[{i}][exercise_name]', '').strip()
            ex_id   = f.get(f'exercises[{i}][exercise_id]', '').strip()
            sets_r  = f.get(f'exercises[{i}][sets_reps]', '').strip() or None
            if ex_name:
                exercises_out.append({
                    'exercise_id':   int(ex_id) if ex_id.isdigit() else None,
                    'exercise_name': ex_name,
                    'sets_reps':     sets_r,
                })
            i += 1
        focus = f.get('focus', '').strip() or None
        tmpl = WorkoutTemplate(
            name=f['name'],
            description=f.get('description') or None,
            workout_type='strength',
            source=f.get('source') or None,
            template_data=json.dumps({'focus': focus, 'exercises': exercises_out}),
        )
        db.session.add(tmpl)
        db.session.commit()
        return redirect(url_for('plans.index') + '#templates-section')
    return render_template('workout_templates/new_strength.html', exercises=_all_exercises())


# ── Circuit template ───────────────────────────────────────────────────────────

@workout_templates_bp.route('/new/circuit', methods=['GET', 'POST'])
def new_circuit():
    circuit_type = request.args.get('type', 'amrap')
    if request.method == 'POST':
        f = request.form
        circuit_type = f.get('circuit_type', 'amrap')
        exercises = []
        i = 0
        while f.get(f'exercises[{i}][name]') is not None:
            name = f.get(f'exercises[{i}][name]', '').strip()
            if name:
                exercises.append({
                    'name': name,
                    'reps': int(f.get(f'exercises[{i}][reps]', 0) or 0),
                    'weight_lbs': float(f.get(f'exercises[{i}][weight_lbs]', 0) or 0) or None,
                    'distance_m': int(f.get(f'exercises[{i}][distance_m]', 0) or 0) or None,
                    'notes': f.get(f'exercises[{i}][notes]', '').strip() or None,
                })
            i += 1
        data = {
            'circuit_type': circuit_type,
            'time_cap_min': int(f.get('time_cap_min', 0) or 0) or None,
            'rounds_target': int(f.get('rounds_target', 0) or 0) or None,
            'exercises': exercises,
        }
        tmpl = WorkoutTemplate(
            name=f['name'],
            description=f.get('description') or None,
            workout_type='circuit',
            source=f.get('source') or None,
            template_data=json.dumps(data),
        )
        db.session.add(tmpl)
        db.session.commit()
        return redirect(url_for('plans.index') + '#templates-section')
    return render_template('workout_templates/new_circuit.html',
                           circuit_type=circuit_type, exercises=_all_exercises())


# ── Hyrox template ─────────────────────────────────────────────────────────────

@workout_templates_bp.route('/new/hyrox', methods=['GET', 'POST'])
def new_hyrox():
    if request.method == 'POST':
        f = request.form
        stations = []
        i = 0
        while f.get(f'stations[{i}][name]') is not None:
            name = f.get(f'stations[{i}][name]', '').strip()
            if name:
                stations.append({
                    'name': name,
                    'distance_m': int(f.get(f'stations[{i}][distance_m]', 0) or 0) or None,
                    'reps': int(f.get(f'stations[{i}][reps]', 0) or 0) or None,
                })
            i += 1
        data = {'stations': stations}
        tmpl = WorkoutTemplate(
            name=f['name'],
            description=f.get('description') or None,
            workout_type='hyrox',
            source=f.get('source') or None,
            template_data=json.dumps(data),
        )
        db.session.add(tmpl)
        db.session.commit()
        return redirect(url_for('plans.index') + '#templates-section')
    return render_template('workout_templates/new_hyrox.html')


# ── Edit ───────────────────────────────────────────────────────────────────────

@workout_templates_bp.route('/<int:tmpl_id>/edit', methods=['GET', 'POST'])
def edit(tmpl_id):
    tmpl = WorkoutTemplate.query.get_or_404(tmpl_id)
    try:
        parsed = json.loads(tmpl.template_data) if tmpl.template_data else {}
    except Exception:
        parsed = {}

    if request.method == 'POST':
        f = request.form
        tmpl.name = f['name']
        tmpl.description = f.get('description') or None
        tmpl.source = f.get('source') or None

        if tmpl.workout_type == 'strength':
            exercises_out = []
            i = 0
            while f.get(f'exercises[{i}][exercise_name]') is not None or f.get(f'exercises[{i}][exercise_id]') is not None:
                ex_name = f.get(f'exercises[{i}][exercise_name]', '').strip()
                ex_id   = f.get(f'exercises[{i}][exercise_id]', '').strip()
                sets_r  = f.get(f'exercises[{i}][sets_reps]', '').strip() or None
                if ex_name:
                    exercises_out.append({
                        'exercise_id':   int(ex_id) if ex_id.isdigit() else None,
                        'exercise_name': ex_name,
                        'sets_reps':     sets_r,
                    })
                i += 1
            focus = f.get('focus', '').strip() or None
            tmpl.template_data = json.dumps({'focus': focus, 'exercises': exercises_out})

        elif tmpl.workout_type == 'circuit':
            exercises = []
            i = 0
            while f.get(f'exercises[{i}][name]') is not None:
                name = f.get(f'exercises[{i}][name]', '').strip()
                if name:
                    exercises.append({
                        'name': name,
                        'reps': int(f.get(f'exercises[{i}][reps]', 0) or 0),
                        'weight_lbs': float(f.get(f'exercises[{i}][weight_lbs]', 0) or 0) or None,
                        'distance_m': int(f.get(f'exercises[{i}][distance_m]', 0) or 0) or None,
                        'notes': f.get(f'exercises[{i}][notes]', '').strip() or None,
                    })
                i += 1
            existing = parsed if isinstance(parsed, dict) else {}
            existing['circuit_type'] = f.get('circuit_type', existing.get('circuit_type', 'amrap'))
            existing['time_cap_min'] = int(f.get('time_cap_min', 0) or 0) or None
            existing['rounds_target'] = int(f.get('rounds_target', 0) or 0) or None
            existing['exercises'] = exercises
            tmpl.template_data = json.dumps(existing)

        elif tmpl.workout_type == 'hyrox':
            stations = []
            i = 0
            while f.get(f'stations[{i}][name]') is not None:
                name = f.get(f'stations[{i}][name]', '').strip()
                if name:
                    stations.append({
                        'name': name,
                        'distance_m': int(f.get(f'stations[{i}][distance_m]', 0) or 0) or None,
                        'reps': int(f.get(f'stations[{i}][reps]', 0) or 0) or None,
                    })
                i += 1
            tmpl.template_data = json.dumps({'stations': stations})

        db.session.commit()
        return redirect(url_for('plans.index') + '#templates-section')

    return render_template('workout_templates/edit.html',
                           tmpl=tmpl, parsed=parsed,
                           presets=HYROX_PRESET_LABELS,
                           exercises=_all_exercises())


# ── Delete ─────────────────────────────────────────────────────────────────────

@workout_templates_bp.route('/<int:tmpl_id>/delete', methods=['POST'])
def delete(tmpl_id):
    tmpl = WorkoutTemplate.query.get_or_404(tmpl_id)
    db.session.delete(tmpl)
    db.session.commit()
    return redirect(url_for('plans.index') + '#templates-section')


# ── Start ──────────────────────────────────────────────────────────────────────

@workout_templates_bp.route('/<int:tmpl_id>/start')
def start(tmpl_id):
    tmpl = WorkoutTemplate.query.get_or_404(tmpl_id)
    try:
        data = json.loads(tmpl.template_data) if tmpl.template_data else {}
    except Exception:
        data = {}

    if tmpl.workout_type == 'hyrox':
        return redirect(url_for('workouts.log_hyrox_training') + f'?template_id={tmpl.id}')

    all_exercises = Exercise.query.order_by(Exercise.name).all()
    ex_map = {e.name.lower(): e for e in all_exercises}

    if tmpl.workout_type == 'strength':
        exercise_list = data if isinstance(data, list) else data.get('exercises', [])
        matched = []
        for item in exercise_list:
            if isinstance(item, str):
                # Old format: free-text string like "Bench Press 4x8-10"
                cleaned = clean_exercise_name(item)
                found   = fuzzy_match(cleaned, ex_map)
                matched.append({'name': item, 'exercise': found, 'sets_reps': ''})
            else:
                # New format: dict with exercise_id, exercise_name, sets_reps
                ex_id = item.get('exercise_id')
                found = (Exercise.query.get(ex_id) if ex_id
                         else fuzzy_match(clean_exercise_name(item.get('exercise_name', '')), ex_map))
                matched.append({
                    'name':      item.get('exercise_name', ''),
                    'exercise':  found,
                    'sets_reps': item.get('sets_reps', '') or '',
                })
        return render_template('workout_templates/start_strength.html',
                               tmpl=tmpl, matched=matched,
                               all_exercises=all_exercises,
                               weight_unit=session.get('weight_unit', 'lbs'))

    elif tmpl.workout_type == 'circuit':
        exercises = data.get('exercises', []) if isinstance(data, dict) else []
        matched = []
        for ex in exercises:
            cleaned = clean_exercise_name(ex.get('name', ''))
            found = fuzzy_match(cleaned, ex_map)
            matched.append({'raw': ex, 'exercise': found})
        return render_template('workout_templates/start_circuit.html',
                               tmpl=tmpl, data=data, matched=matched,
                               all_exercises=all_exercises,
                               weight_unit=session.get('weight_unit', 'lbs'))

    return redirect(url_for('plans.index'))


# ── Select ─────────────────────────────────────────────────────────────────────

@workout_templates_bp.route('/select')
def select():
    templates = WorkoutTemplate.query.order_by(WorkoutTemplate.name).all()
    for t in templates:
        try:
            t._parsed = json.loads(t.template_data) if t.template_data else {}
        except Exception:
            t._parsed = {}
    return render_template('workout_templates/select.html', templates=templates)


# ── HTMX partials ──────────────────────────────────────────────────────────────

@workout_templates_bp.route('/htmx/exercise-row')
def htmx_exercise_row():
    index = request.args.get('index', 0, type=int)
    return render_template('partials/template_exercise_row.html', index=index)


@workout_templates_bp.route('/htmx/circuit-exercise-row')
def htmx_circuit_exercise_row():
    index = request.args.get('index', 0, type=int)
    return render_template('partials/template_circuit_exercise_row.html', index=index)
