from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from sqlalchemy import func
from ..models import db, Exercise

exercises_bp = Blueprint('exercises', __name__)


@exercises_bp.route('/')
def index():
    category_filter = request.args.get('category', '')
    muscle_filter   = request.args.get('muscle', '')
    exercises = Exercise.query.order_by(Exercise.category, Exercise.name).all()

    # Muscle group pills only for strength exercises
    all_muscles = sorted(set(e.muscle_group for e in exercises
                             if e.muscle_group and e.category not in ('cardio', 'mobility')))

    if category_filter in ('cardio', 'mobility'):
        exercises = [e for e in exercises if e.category == category_filter]
    elif muscle_filter:
        exercises = [e for e in exercises if e.muscle_group == muscle_filter]

    grouped = {}
    for ex in exercises:
        grouped.setdefault(ex.category or 'other', []).append(ex)

    return render_template('exercises/index.html', grouped=grouped,
                           all_muscles=all_muscles,
                           muscle_filter=muscle_filter,
                           category_filter=category_filter)


@exercises_bp.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == 'POST':
        f = request.form
        ex = Exercise(name=f['name'], muscle_group=f.get('muscle_group'), category=f.get('category', 'strength'))
        db.session.add(ex)
        db.session.commit()
        return redirect(url_for('exercises.index'))
    return render_template('exercises/new.html')


@exercises_bp.route('/<int:ex_id>/edit', methods=['GET', 'POST'])
def edit(ex_id):
    ex = Exercise.query.get_or_404(ex_id)
    if request.method == 'POST':
        f = request.form
        ex.name         = f['name']
        ex.muscle_group = f.get('muscle_group', ex.muscle_group)
        ex.category     = f.get('category', ex.category)
        db.session.commit()
        return redirect(url_for('exercises.index'))
    return render_template('exercises/edit.html', ex=ex)


@exercises_bp.route('/<int:ex_id>/delete', methods=['POST'])
def delete(ex_id):
    ex = Exercise.query.get_or_404(ex_id)
    db.session.delete(ex)
    db.session.commit()
    return redirect(url_for('exercises.index'))


@exercises_bp.route('/find-or-create', methods=['POST'])
def find_or_create():
    data = request.get_json(force=True)
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400

    existing = Exercise.query.filter(func.lower(Exercise.name) == func.lower(name)).first()
    if existing:
        return jsonify({
            'id': existing.id,
            'name': existing.name,
            'muscle_group': existing.muscle_group or '',
            'created': False,
        })

    muscle_group = (data.get('muscle_group') or '').strip() or None
    category     = (data.get('category') or 'strength').strip()
    ex = Exercise(name=name, muscle_group=muscle_group, category=category)
    db.session.add(ex)
    db.session.commit()
    return jsonify({
        'id': ex.id,
        'name': ex.name,
        'muscle_group': ex.muscle_group or '',
        'created': True,
    }), 201