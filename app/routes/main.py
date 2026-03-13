from flask import Blueprint, render_template, session, redirect, request, url_for, current_app
from sqlalchemy import func, extract
from datetime import datetime, timedelta, date
from ..models import db, Workout, WorkoutSet, Run, WorkoutPlan, HyroxResult

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