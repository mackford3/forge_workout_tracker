from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from ..models import db, Program, ProgramPhase, ProgramDay, ProgramCompletion, Workout
from datetime import date, timedelta
import json

program_bp = Blueprint('program', __name__)


def _current_week(program):
    """Return (week_number, day_number) for today based on program start_date."""
    if not program.start_date:
        return 1, 1
    today    = date.today()
    delta    = (today - program.start_date).days
    week_num = min((delta // 7) + 1, program.total_weeks)
    day_num  = (delta % 7) + 1
    return week_num, day_num


def _completion_map(program_id):
    """Return {day_id: ProgramCompletion} for a program."""
    comps = (ProgramCompletion.query
             .join(ProgramDay)
             .filter(ProgramDay.program_id == program_id)
             .all())
    return {c.day_id: c for c in comps}


@program_bp.route('/')
def index():
    programs = Program.query.order_by(Program.is_active.desc(), Program.created_at.desc()).all()
    # Attach current week info to active program
    active = next((p for p in programs if p.is_active), None)
    current_week = current_day = None
    today_day = None
    if active:
        current_week, current_day = _current_week(active)
        today_day = (ProgramDay.query
                     .filter_by(program_id=active.id,
                                week_number=current_week,
                                day_number=current_day)
                     .first())
    return render_template('program/index.html',
        programs=programs, active=active,
        current_week=current_week, today_day=today_day)


@program_bp.route('/<int:program_id>')
def view(program_id):
    program  = Program.query.get_or_404(program_id)
    phases   = program.phases.all()
    comp_map = _completion_map(program_id)
    current_week, current_day_num = _current_week(program)

    # Group days by phase → week
    phase_weeks = {}
    for phase in phases:
        weeks = {}
        days  = (ProgramDay.query
                 .filter_by(program_id=program_id, phase_id=phase.id)
                 .order_by(ProgramDay.week_number, ProgramDay.day_number)
                 .all())
        for d in days:
            comp = comp_map.get(d.id)
            d._completed  = comp.completed if comp else False
            d._workout_id = comp.workout_id if comp else None
            d._done_date  = comp.done_date  if comp else None
            weeks.setdefault(d.week_number, []).append(d)
        phase_weeks[phase.id] = {'phase': phase, 'weeks': weeks}

    return render_template('program/view.html',
        program=program, phases=phases, phase_weeks=phase_weeks,
        current_week=current_week, current_day_num=current_day_num,
        comp_map=comp_map)


@program_bp.route('/<int:program_id>/week/<int:week_num>')
def week(program_id, week_num):
    program  = Program.query.get_or_404(program_id)
    days     = (ProgramDay.query
                .filter_by(program_id=program_id, week_number=week_num)
                .order_by(ProgramDay.day_number).all())
    comp_map = _completion_map(program_id)
    current_week, current_day_num = _current_week(program)

    # Attach phase name
    phase_ids = set(d.phase_id for d in days if d.phase_id)
    phases    = {p.id: p for p in ProgramPhase.query.filter(ProgramPhase.id.in_(phase_ids)).all()}

    for d in days:
        comp = comp_map.get(d.id)
        d._completed  = comp.completed if comp else False
        d._workout_id = comp.workout_id if comp else None
        d._done_date  = comp.done_date  if comp else None
        try:
            d._exercises = json.loads(d.exercises) if d.exercises else []
        except Exception:
            d._exercises = []

    # Deload / taper flags
    is_deload = week_num in (4, 8, 12, 16, 20)
    is_taper  = week_num in (23, 24)

    prev_week = week_num - 1 if week_num > 1 else None
    next_week = week_num + 1 if week_num < program.total_weeks else None

    return render_template('program/week.html',
        program=program, days=days, week_num=week_num,
        phases=phases, comp_map=comp_map,
        current_week=current_week, current_day_num=current_day_num,
        is_deload=is_deload, is_taper=is_taper,
        prev_week=prev_week, next_week=next_week)


@program_bp.route('/day/<int:day_id>/complete', methods=['POST'])
def complete_day(day_id):
    day  = ProgramDay.query.get_or_404(day_id)
    comp = ProgramCompletion.query.filter_by(day_id=day_id).first()
    if not comp:
        comp = ProgramCompletion(day_id=day_id)
        db.session.add(comp)
    comp.completed = True
    comp.done_date = date.today()
    db.session.commit()
    # Return to the week view
    return redirect(url_for('program.week',
        program_id=day.program_id, week_num=day.week_number))


@program_bp.route('/day/<int:day_id>/uncomplete', methods=['POST'])
def uncomplete_day(day_id):
    day  = ProgramDay.query.get_or_404(day_id)
    comp = ProgramCompletion.query.filter_by(day_id=day_id).first()
    if comp:
        comp.completed = False
        comp.done_date = None
        db.session.commit()
    return redirect(url_for('program.week',
        program_id=day.program_id, week_num=day.week_number))


@program_bp.route('/<int:program_id>/activate', methods=['POST'])
def activate(program_id):
    Program.query.update({'is_active': False})
    p = Program.query.get_or_404(program_id)
    p.is_active = True
    db.session.commit()
    return redirect(url_for('program.index'))