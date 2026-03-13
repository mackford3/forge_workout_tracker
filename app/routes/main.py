from flask import Blueprint, render_template, session, redirect, request, url_for, current_app
from sqlalchemy import func, extract
from datetime import datetime, timedelta, date
from ..models import db, Workout, WorkoutSet, Run, WorkoutPlan, HyroxResult
from sqlalchemy import extract as db_extract

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    now = datetime.utcnow()
    year = now.year

    ytd_workouts = Workout.query.filter(
        extract('year', Workout.completed_at) == year
    ).count()

    ytd_weight = db.session.query(
        func.sum(WorkoutSet.weight_lbs * WorkoutSet.reps)
    ).join(Workout).filter(
        extract('year', Workout.completed_at) == year,
        WorkoutSet.weight_lbs.isnot(None),
        WorkoutSet.reps.isnot(None),
        WorkoutSet.skipped.is_(False)
    ).scalar() or 0

    ytd_distance = db.session.query(
        func.sum(Run.total_distance_km)
    ).join(Workout).filter(
        extract('year', Workout.completed_at) == year
    ).scalar() or 0

    ytd_run_time = db.session.query(
        func.sum(Run.total_duration_s)
    ).join(Workout).filter(
        extract('year', Workout.completed_at) == year
    ).scalar() or 0

    ytd_calories = db.session.query(
        func.sum(Workout.calories)
    ).filter(
        extract('year', Workout.completed_at) == year,
        Workout.calories.isnot(None)
    ).scalar() or 0

    # ── Streaks ────────────────────────────────────────────
    # Get all distinct workout dates (local date, deduplicated)
    all_dates_raw = db.session.query(
        func.date(Workout.completed_at)
    ).order_by(func.date(Workout.completed_at).desc()).distinct().all()
    all_dates = sorted(set(r[0] for r in all_dates_raw), reverse=True)

    today = datetime.utcnow().date()
    current_streak = 0
    longest_streak = 0

    if all_dates:
        # Current streak — count back from today or yesterday
        check = today
        for d in all_dates:
            if d == check or d == check - timedelta(days=1):
                current_streak += 1
                check = d - timedelta(days=1)
            elif d < check - timedelta(days=1):
                break

        # Longest streak — sliding window over sorted ascending dates
        asc = sorted(all_dates)
        run = 1
        for i in range(1, len(asc)):
            if (asc[i] - asc[i-1]).days == 1:
                run += 1
                longest_streak = max(longest_streak, run)
            else:
                run = 1
        longest_streak = max(longest_streak, run)

    last_workout = Workout.query.order_by(Workout.completed_at.desc()).first()
    active_plan  = WorkoutPlan.query.filter_by(is_active=True).first()
    recent_workouts = Workout.query.order_by(Workout.completed_at.desc()).limit(6).all()

    type_counts = db.session.query(
        Workout.workout_type, func.count(Workout.id)
    ).filter(
        extract('year', Workout.completed_at) == year
    ).group_by(Workout.workout_type).all()

    # Location breakdown
    location_counts = db.session.query(
        Workout.location, func.count(Workout.id)
    ).filter(
        extract('year', Workout.completed_at) == year
    ).group_by(Workout.location).all()

    return render_template('index.html',
        ytd_workouts=ytd_workouts,
        ytd_weight=float(ytd_weight),
        ytd_distance=float(ytd_distance),
        ytd_run_time=int(ytd_run_time),
        ytd_calories=int(ytd_calories),
        last_workout=last_workout,
        active_plan=active_plan,
        recent_workouts=recent_workouts,
        type_counts=dict(type_counts),
        location_counts=dict(location_counts),
        year=year,
        current_streak=current_streak,
        longest_streak=longest_streak,
    )


@main_bp.route('/set-unit/<unit>')
def set_unit(unit):
    """Toggle weight unit preference stored in session."""
    if unit in ('kg', 'lbs'):
        session['weight_unit'] = unit
    return ('', 204)


# ── Calendar view ──────────────────────────────────────────
@main_bp.route('/calendar')
@main_bp.route('/calendar/<int:year>/<int:month>')
def calendar(year=None, month=None):
    from calendar import monthcalendar
    now = datetime.utcnow()
    year  = year  or now.year
    month = month or now.month

    # All workouts in this month
    from ..models import Workout
    workouts = Workout.query.filter(
        db_extract('year',  Workout.completed_at) == year,
        db_extract('month', Workout.completed_at) == month,
    ).order_by(Workout.completed_at).all()

    # Build day_map: {day_int: [workout, ...]}
    day_map = {}
    for w in workouts:
        d = w.completed_at.day
        day_map.setdefault(d, []).append(w)

    # Prev / next month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    import calendar as cal_mod
    cal_weeks  = monthcalendar(year, month)
    month_name = cal_mod.month_name[month]

    workout_ids = [w.id for w in workouts]

    # ── Month summary stats ─────────────────────────────────
    # Total weight lifted
    month_weight = 0
    month_prs    = 0
    if workout_ids:
        from ..models import WorkoutSet, Run, RunSegment
        wt = db.session.query(
            func.sum(WorkoutSet.weight_lbs * WorkoutSet.reps)
        ).filter(
            WorkoutSet.workout_id.in_(workout_ids),
            WorkoutSet.weight_lbs.isnot(None),
            WorkoutSet.reps.isnot(None),
            WorkoutSet.skipped.is_(False),
        ).scalar()
        month_weight = float(wt) if wt else 0

        # PRs: sets where weight equals all-time max for that exercise up to that date
        all_sets = db.session.query(WorkoutSet).filter(
            WorkoutSet.workout_id.in_(workout_ids),
            WorkoutSet.weight_lbs.isnot(None),
            WorkoutSet.skipped.is_(False),
        ).all()
        for s in all_sets:
            lifetime_max = db.session.query(func.max(WorkoutSet.weight_lbs))                 .join(Workout)                 .filter(
                    WorkoutSet.exercise_id == s.exercise_id,
                    WorkoutSet.skipped.is_(False),
                    Workout.completed_at <= s.workout.completed_at,
                ).scalar()
            if lifetime_max and abs(float(s.weight_lbs) - float(lifetime_max)) < 0.01:
                month_prs += 1

        # Distance: sum run totals + segment fallback
        month_distance = 0
        runs = db.session.query(Run).filter(Run.workout_id.in_(workout_ids)).all()
        for r in runs:
            if r.total_distance_km:
                month_distance += float(r.total_distance_km)
            else:
                seg_dist = db.session.query(func.sum(RunSegment.distance_km))                     .filter(RunSegment.run_id == r.id, RunSegment.skipped.is_(False)).scalar()
                if seg_dist:
                    month_distance += float(seg_dist)
    else:
        month_distance = 0

    return render_template('calendar.html',
        year=year, month=month, month_name=month_name,
        cal_weeks=cal_weeks, day_map=day_map,
        prev_year=prev_year, prev_month=prev_month,
        next_year=next_year, next_month=next_month,
        today=datetime.utcnow().date(),
        month_weight=month_weight,
        month_distance=month_distance,
        month_prs=month_prs,
    )