from flask import Blueprint, render_template, request, redirect, url_for
from datetime import date
from ..models import db, WorkoutPlan, PlanDay

plans_bp = Blueprint('plans', __name__)

DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


@plans_bp.route('/')
def index():
    plans = WorkoutPlan.query.order_by(WorkoutPlan.created_at.desc()).all()
    from ..models import Program, ProgramDay, ProgramCompletion
    from ..routes.program import _completion_week, _is_done, _completion_map
    programs = Program.query.order_by(Program.is_active.desc(), Program.created_at.desc()).all()

    # Attach completion progress to each program
    for p in programs:
        all_days  = ProgramDay.query.filter_by(program_id=p.id).all()
        active    = [d for d in all_days if d.name and 'Rest' not in d.name]
        comp_map  = _completion_map(p.id)
        done      = sum(1 for d in active if _is_done(comp_map.get(d.id)))
        total     = len(active)
        p.done_sessions  = done
        p.total_sessions = total
        p.progress_pct   = int(done / total * 100) if total > 0 else 0
        p.comp_week      = _completion_week(p.id)

    return render_template('plans/index.html', plans=plans, programs=programs, today=date.today())


@plans_bp.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        f = request.form
        plan = WorkoutPlan(
            name=f['name'],
            description=f.get('description')
        )
        db.session.add(plan)
        db.session.flush()

        # Parse plan days
        i = 0
        while f.get(f'days[{i}][name]') is not None:
            day = PlanDay(
                plan_id=plan.id,
                week_number=int(f.get(f'days[{i}][week]', 1)),
                day_of_week=f.get(f'days[{i}][dow]', 'Mon'),
                name=f.get(f'days[{i}][name]', ''),
                notes=f.get(f'days[{i}][notes]', ''),
                order_index=i
            )
            db.session.add(day)
            i += 1

        db.session.commit()
        return redirect(url_for('plans.view', plan_id=plan.id))
    return render_template('plans/new.html', days_of_week=DAYS_OF_WEEK)


@plans_bp.route('/<int:plan_id>')
def view(plan_id):
    plan = WorkoutPlan.query.get_or_404(plan_id)
    days = PlanDay.query.filter_by(plan_id=plan_id).order_by(PlanDay.week_number, PlanDay.order_index).all()
    # Group by week
    weeks = {}
    for day in days:
        weeks.setdefault(day.week_number, []).append(day)
    return render_template('plans/view.html', plan=plan, weeks=weeks)


@plans_bp.route('/<int:plan_id>/activate', methods=['POST'])
def activate(plan_id):
    # Deactivate all
    WorkoutPlan.query.update({'is_active': False})
    # Activate selected
    plan = WorkoutPlan.query.get_or_404(plan_id)
    plan.is_active = True
    db.session.commit()
    return redirect(url_for('main.index'))


@plans_bp.route('/<int:plan_id>/deactivate', methods=['POST'])
def deactivate(plan_id):
    plan = WorkoutPlan.query.get_or_404(plan_id)
    plan.is_active = False
    db.session.commit()
    return redirect(url_for('plans.index'))


@plans_bp.route('/<int:plan_id>/delete', methods=['POST'])
def delete(plan_id):
    plan = WorkoutPlan.query.get_or_404(plan_id)
    db.session.delete(plan)
    db.session.commit()
    return redirect(url_for('plans.index'))


@plans_bp.route('/htmx/plan-day-row')
def htmx_plan_day_row():
    index = request.args.get('index', 0, type=int)
    return render_template('partials/plan_day_row.html', index=index, days_of_week=DAYS_OF_WEEK)