from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
from ..models import db, Program, ProgramPhase, ProgramDay, ProgramCompletion, Workout, Exercise
from datetime import date, timedelta
import json
import re

program_bp = Blueprint('program', __name__)


def _clean_exercise_name(name):
    """Strip trailing set/rep/duration info from a planned workout exercise name."""
    n = name.strip()
    n = re.sub(r'\s+\d+x\d+[/\w]*$', '', n)                      # "3x10/side"
    n = re.sub(r'\s+[\d\-]+min$', '', n)                           # "10min", "30-45min"
    n = re.sub(r'\s+Zone\s+\d+$', '', n, flags=re.IGNORECASE)     # "Zone 2"
    n = re.sub(r'\s+\([^)]*\)\s*$', '', n)                        # trailing "(hips/shoulders)"
    return n.lower().strip()


def _fuzzy_match(cleaned_name, ex_map):
    """Match a cleaned name against exercise map. Handles 'X or Y' alternatives."""
    if ' or ' in cleaned_name:
        for part in cleaned_name.split(' or '):
            result = _fuzzy_match(part.strip(), ex_map)
            if result:
                return result
    clean = re.sub(r'[^\w\s]', '', cleaned_name).lower()
    words = clean.split()
    for length in range(len(words), 0, -1):
        candidate = words[:length]
        for k, ex in ex_map.items():
            if all(w in k for w in candidate):
                return ex
    return None

STATUS_COLORS = {
    'done':    '#4caf50',
    'skipped': '#ff4444',
    'altered': '#ff9800',
    'delayed': '#9e9e9e',
}


def _completion_map(program_id):
    comps = (ProgramCompletion.query
             .join(ProgramDay)
             .filter(ProgramDay.program_id == program_id)
             .all())
    return {c.day_id: c for c in comps}


def _progress(program_id):
    """Return (completed_count, total_active_count) based on completions only."""
    all_days = ProgramDay.query.filter_by(program_id=program_id).all()
    active   = [d for d in all_days if d.name and 'Rest' not in d.name]
    comp_map = _completion_map(program_id)
    done     = sum(1 for d in active if _is_done(comp_map.get(d.id)))
    return done, len(active)


def _calendar_week(program):
    """Week/day based on calendar (start_date). Used only for 'scheduled' view."""
    if not program.start_date:
        return 1, 1
    today    = date.today()
    delta    = (today - program.start_date).days
    week_num = min((delta // 7) + 1, program.total_weeks)
    day_num  = (delta % 7) + 1
    return week_num, day_num


def _is_done(comp):
    """A completion counts as done if status='done', 'altered', or legacy completed=True."""
    if comp is None:
        return False
    if comp.status in ('done', 'altered'):
        return True
    if comp.status is None and comp.completed:
        return True
    return False


def _completion_week(program_id):
    """
    Current week based on completions.
    Returns the week containing the most recently completed workout,
    or the next week if that week is fully done.
    Falls back to week 1 if nothing is completed.
    """
    comp_map = _completion_map(program_id)

    # Find the highest week number that has at least one completed active day
    latest_done_week = 0
    for week_num in range(1, 25):
        days = ProgramDay.query.filter_by(
            program_id=program_id, week_number=week_num
        ).order_by(ProgramDay.day_number).all()
        if not days:
            break
        active = [d for d in days if d.name and 'Rest' not in d.name]
        if any(_is_done(comp_map.get(d.id)) for d in active):
            latest_done_week = week_num

    if latest_done_week == 0:
        return 1

    # Check if that week is fully complete
    days = ProgramDay.query.filter_by(
        program_id=program_id, week_number=latest_done_week
    ).all()
    active = [d for d in days if d.name and 'Rest' not in d.name]
    all_done = all(_is_done(comp_map.get(d.id)) for d in active)

    if all_done:
        return min(latest_done_week + 1, 24)
    return latest_done_week


@program_bp.route('/')
def index():
    programs = Program.query.order_by(Program.is_active.desc(), Program.created_at.desc()).all()
    active   = next((p for p in programs if p.is_active), None)
    today_day = comp_week = cal_week = None
    if active:
        comp_week = _completion_week(active.id)
        cal_week, cal_day = _calendar_week(active)
        today_day = ProgramDay.query.filter_by(
            program_id=active.id,
            week_number=cal_week,
            day_number=cal_day
        ).first()
    return render_template('program/index.html',
        programs=programs, active=active,
        current_week=comp_week, cal_week=cal_week, today_day=today_day)


@program_bp.route('/<int:program_id>')
def view(program_id):
    program  = Program.query.get_or_404(program_id)
    phases   = program.phases.all()
    comp_map = _completion_map(program_id)
    comp_week = _completion_week(program_id)
    done_count, total_count = _progress(program_id)

    phase_weeks = {}
    for phase in phases:
        weeks = {}
        days  = (ProgramDay.query
                 .filter_by(program_id=program_id, phase_id=phase.id)
                 .order_by(ProgramDay.week_number, ProgramDay.day_number).all())
        for d in days:
            comp = comp_map.get(d.id)
            d._comp      = comp
            d._completed = comp and comp.status == 'done'
            d._status    = comp.status if comp else None
            weeks.setdefault(d.week_number, []).append(d)
        phase_weeks[phase.id] = {'phase': phase, 'weeks': weeks}

    return render_template('program/view.html',
        program=program, phases=phases, phase_weeks=phase_weeks,
        current_week=comp_week, done_count=done_count, total_count=total_count,
        status_colors=STATUS_COLORS, comp_map=comp_map)


@program_bp.route('/<int:program_id>/week/<int:week_num>')
def week(program_id, week_num):
    program  = Program.query.get_or_404(program_id)
    days     = (ProgramDay.query
                .filter_by(program_id=program_id, week_number=week_num)
                .order_by(ProgramDay.day_number).all())
    comp_map = _completion_map(program_id)
    comp_week = _completion_week(program_id)
    cal_week, cal_day_num = _calendar_week(program)

    phase_ids = set(d.phase_id for d in days if d.phase_id)
    phases    = {p.id: p for p in ProgramPhase.query.filter(ProgramPhase.id.in_(phase_ids)).all()}

    for d in days:
        comp = comp_map.get(d.id)
        d._comp       = comp
        d._completed  = comp and comp.status == 'done'
        d._status     = comp.status if comp else None
        d._workout_id = comp.workout_id if comp else None
        d._done_date  = comp.done_date  if comp else None
        try:
            d._exercises = json.loads(d.exercises) if d.exercises else []
        except Exception:
            d._exercises = []

    is_deload = week_num in (4, 8, 12, 16, 20)
    is_taper  = week_num in (23, 24)
    prev_week = week_num - 1 if week_num > 1 else None
    next_week = week_num + 1 if week_num < program.total_weeks else None

    done  = sum(1 for d in days if _is_done(comp_map.get(d.id)))
    total = sum(1 for d in days if d.name and 'Rest' not in d.name)

    return render_template('program/week.html',
        program=program, days=days, week_num=week_num,
        phases=phases, comp_map=comp_map,
        current_week=comp_week, cal_week=cal_week, cal_day_num=cal_day_num,
        is_deload=is_deload, is_taper=is_taper,
        prev_week=prev_week, next_week=next_week,
        done=done, total=total,
        status_colors=STATUS_COLORS)


@program_bp.route('/day/<int:day_id>/start')
def start_day(day_id):
    """Pre-populate a strength log form with exercises from this program day."""
    day     = ProgramDay.query.get_or_404(day_id)
    program = Program.query.get(day.program_id)

    # Route Hyrox-labelled days to the Hyrox training logger
    day_name_lower = (day.name or '').lower()
    if 'hyrox' in day_name_lower:
        preset_key = 'full_sim'
        if 'half' in day_name_lower:
            preset_key = 'half_sim_b' if (' b' in day_name_lower or 'b side' in day_name_lower) else 'half_sim_a'
        elif 'station' in day_name_lower or ('workout' in day_name_lower and 'sim' not in day_name_lower):
            preset_key = 'workouts_only'
        elif 'run' in day_name_lower and 'sim' not in day_name_lower:
            preset_key = 'running_only'
        return redirect(url_for('workouts.log_hyrox_training',
                                preset=preset_key, program_day_id=day_id))

    try:
        exercise_names = json.loads(day.exercises) if day.exercises else []
    except Exception:
        exercise_names = []

    # Match exercise names to DB exercise IDs (fuzzy: contains match)
    all_exercises = Exercise.query.order_by(Exercise.name).all()
    ex_map = {e.name.lower(): e for e in all_exercises}

    matched = []
    for name in exercise_names:
        cleaned = _clean_exercise_name(name)
        found   = _fuzzy_match(cleaned, ex_map)
        matched.append({'name': name, 'exercise': found})

    return render_template('program/start_workout.html',
        day=day, program=program, matched=matched,
        all_exercises=all_exercises,
        weight_unit=session.get('weight_unit', 'lbs'))


@program_bp.route('/day/<int:day_id>/status', methods=['POST'])
def set_status(day_id):
    day    = ProgramDay.query.get_or_404(day_id)
    status = request.form.get('status')  # done/skipped/altered/delayed
    notes  = request.form.get('notes', '')
    week_num = day.week_number

    comp = ProgramCompletion.query.filter_by(day_id=day_id).first()
    if not comp:
        comp = ProgramCompletion(day_id=day_id)
        db.session.add(comp)

    comp.status = status
    comp.notes  = notes

    if status == 'done':
        comp.completed = True
        comp.done_date = date.today()
    elif status == 'skipped':
        comp.completed  = False
        comp.skipped_at = date.today()
    elif status == 'altered':
        comp.completed = True
        comp.done_date = date.today()
    elif status == 'delayed':
        comp.completed = False
        # Don't shift the whole plan — just mark this day as delayed
        # User can re-order manually or just track it as delayed

    db.session.commit()
    return redirect(url_for('program.week',
        program_id=day.program_id, week_num=week_num))


@program_bp.route('/day/<int:day_id>/link', methods=['POST'])
def link_workout(day_id):
    """Link a logged workout to a program day."""
    day       = ProgramDay.query.get_or_404(day_id)
    workout_id = int(request.form['workout_id'])

    comp = ProgramCompletion.query.filter_by(day_id=day_id).first()
    if not comp:
        comp = ProgramCompletion(day_id=day_id)
        db.session.add(comp)

    comp.workout_id = workout_id
    comp.completed  = True
    comp.status     = 'done'
    comp.done_date  = Workout.query.get(workout_id).completed_at.date()
    db.session.commit()
    return redirect(url_for('program.week',
        program_id=day.program_id, week_num=day.week_number))


@program_bp.route('/day/<int:day_id>/edit', methods=['GET', 'POST'])
def edit_day(day_id):
    day = ProgramDay.query.get_or_404(day_id)
    if request.method == 'POST':
        day.name  = request.form.get('name', day.name)
        day.notes = request.form.get('notes', '')
        exercises_raw = request.form.get('exercises', '')
        # Parse newline-separated list into JSON array
        exs = [e.strip() for e in exercises_raw.split('\n') if e.strip()]
        day.exercises = json.dumps(exs)
        db.session.commit()
        return redirect(url_for('program.week',
            program_id=day.program_id, week_num=day.week_number))
    try:
        ex_list = json.loads(day.exercises) if day.exercises else []
    except Exception:
        ex_list = []
    return render_template('program/edit_day.html', day=day, ex_list=ex_list)


@program_bp.route('/<int:program_id>/activate', methods=['POST'])
def activate(program_id):
    Program.query.update({'is_active': False})
    p = Program.query.get_or_404(program_id)
    p.is_active = True
    db.session.commit()
    return redirect(url_for('program.index'))