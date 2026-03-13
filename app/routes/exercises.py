from flask import Blueprint, render_template, request, redirect, url_for
from ..models import db, Exercise

exercises_bp = Blueprint('exercises', __name__)


@exercises_bp.route('/')
def index():
    muscle_filter = request.args.get('muscle', '')
    exercises = Exercise.query.order_by(Exercise.category, Exercise.name).all()

    # All distinct muscle groups for filter pills
    all_muscles = sorted(set(e.muscle_group for e in exercises if e.muscle_group))

    if muscle_filter:
        exercises = [e for e in exercises if e.muscle_group == muscle_filter]

    grouped = {}
    for ex in exercises:
        grouped.setdefault(ex.category or 'other', []).append(ex)

    return render_template('exercises/index.html', grouped=grouped,
                           all_muscles=all_muscles, muscle_filter=muscle_filter)


@exercises_bp.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        f = request.form
        ex = Exercise(name=f['name'], muscle_group=f.get('muscle_group'), category=f.get('category', 'strength'))
        db.session.add(ex)
        db.session.commit()
        return redirect(url_for('exercises.index'))
    return render_template('exercises/new.html')


@exercises_bp.route('/<int:ex_id>/delete', methods=['POST'])
def delete(ex_id):
    ex = Exercise.query.get_or_404(ex_id)
    db.session.delete(ex)
    db.session.commit()
    return redirect(url_for('exercises.index'))