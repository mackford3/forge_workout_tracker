from flask import Blueprint, render_template, request, jsonify
from ..models import db, Exercise, WorkoutSet, Workout
from sqlalchemy import func

progress_bp = Blueprint('progress', __name__)


@progress_bp.route('/')
def index():
    exercises = Exercise.query.filter(
        Exercise.category == 'strength'
    ).order_by(Exercise.name).all()
    return render_template('progress/index.html', exercises=exercises)


@progress_bp.route('/data')
def data():
    ex_id = request.args.get('exercise_id', type=int)
    if not ex_id:
        return jsonify([])

    # Get all sets for this exercise ordered by date
    rows = (
        db.session.query(
            WorkoutSet.weight_lbs,
            WorkoutSet.weight_kg,
            WorkoutSet.reps,
            WorkoutSet.set_number,
            Workout.completed_at,
            Workout.id.label('workout_id'),
            Workout.name.label('workout_name'),
        )
        .join(Workout, Workout.id == WorkoutSet.workout_id)
        .filter(
            WorkoutSet.exercise_id == ex_id,
            WorkoutSet.skipped == False,
            WorkoutSet.weight_lbs != None,
        )
        .order_by(Workout.completed_at.asc())
        .all()
    )

    # Group by workout date — take the max weight lifted per session
    from collections import defaultdict
    by_date = defaultdict(lambda: {'max_lbs': 0, 'max_kg': 0, 'sets': [], 'workout_name': '', 'workout_id': 0})
    for r in rows:
        date_key = r.completed_at.strftime('%Y-%m-%d')
        entry    = by_date[date_key]
        entry['workout_name'] = r.workout_name
        entry['workout_id']   = r.workout_id
        lbs = float(r.weight_lbs) if r.weight_lbs else 0
        kg  = float(r.weight_kg)  if r.weight_kg  else 0
        if lbs > entry['max_lbs']:
            entry['max_lbs'] = lbs
            entry['max_kg']  = kg
        entry['sets'].append({
            'set': r.set_number,
            'lbs': lbs,
            'reps': r.reps,
        })

    result = []
    for date_key in sorted(by_date.keys()):
        e = by_date[date_key]
        result.append({
            'date':         date_key,
            'max_lbs':      e['max_lbs'],
            'max_kg':       e['max_kg'],
            'sets':         e['sets'],
            'workout_name': e['workout_name'],
            'workout_id':   e['workout_id'],
        })

    return jsonify(result)