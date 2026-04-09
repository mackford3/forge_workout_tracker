from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session, Response
from ..models import db, PremadeWorkout, PremadeStation, PremadeResult, PremadeStationResult, Workout
from datetime import datetime

premade_bp = Blueprint('premade', __name__)


def _htmx_or_redirect(url):
    if request.headers.get('HX-Request'):
        resp = Response('', 200)
        resp.headers['HX-Redirect'] = url
        return resp
    return redirect(url)


def _fmt_time(seconds):
    if not seconds:
        return None
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _parse_time(val):
    """Parse MM:SS or HH:MM:SS to seconds."""
    if not val or not val.strip():
        return None
    parts = val.strip().split(':')
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return None
    return None


@premade_bp.route('/')
def index():
    workouts = PremadeWorkout.query.order_by(PremadeWorkout.name).all()
    return render_template('premade/index.html', workouts=workouts)


@premade_bp.route('/<int:pw_id>')
def view(pw_id):
    pw       = PremadeWorkout.query.get_or_404(pw_id)
    stations = pw.stations.all()
    results  = (PremadeResult.query
                .filter_by(premade_workout_id=pw_id)
                .order_by(PremadeResult.done_at.desc()).all())

    # Attach station results to each result
    for r in results:
        r._station_results = {sr.station_id: sr for sr in r.station_results.all()}
        r._fmt_total = _fmt_time(r.total_time_s)

    # Best total time (completed only)
    completed = [r for r in results if r.completed and r.total_time_s]
    best_time_s = min((r.total_time_s for r in completed), default=None)

    return render_template('premade/view.html',
        pw=pw, stations=stations, results=results,
        best_time_s=best_time_s, fmt_time=_fmt_time)


@premade_bp.route('/<int:pw_id>/log', methods=['GET', 'POST'])
def log(pw_id):
    pw       = PremadeWorkout.query.get_or_404(pw_id)
    stations = pw.stations.all()

    if request.method == 'POST':
        f = request.form

        # Create workout header
        workout = Workout(
            workout_type     = 'strength',
            name             = pw.name,
            location         = f.get('location', 'gym'),
            duration_minutes = int(f['duration_minutes']) if f.get('duration_minutes') else None,
            calories         = int(f['calories'])         if f.get('calories')         else None,
            avg_bpm          = int(f['avg_bpm'])          if f.get('avg_bpm')          else None,
            notes            = f.get('notes'),
            completed_at     = datetime.fromisoformat(f['completed_at']) if f.get('completed_at') else datetime.utcnow(),
        )
        db.session.add(workout)
        db.session.flush()

        # Parse total time
        total_s = _parse_time(f.get('total_time'))
        # If not provided, sum station times
        if not total_s:
            total_s = sum(
                _parse_time(f.get(f'station_{s.id}_time')) or 0
                for s in stations
            ) or None

        completed = not f.get('incomplete')

        result = PremadeResult(
            premade_workout_id = pw_id,
            workout_id         = workout.id,
            total_time_s       = total_s,
            completed          = completed,
            notes              = f.get('notes'),
            done_at            = workout.completed_at,
        )
        db.session.add(result)
        db.session.flush()

        for s in stations:
            time_s  = _parse_time(f.get(f'station_{s.id}_time'))
            reps    = int(f[f'station_{s.id}_reps']) if f.get(f'station_{s.id}_reps') else None
            effort  = float(f[f'station_{s.id}_effort']) if f.get(f'station_{s.id}_effort') else None
            skipped = bool(f.get(f'station_{s.id}_skip'))
            snotes  = f.get(f'station_{s.id}_notes', '')

            db.session.add(PremadeStationResult(
                premade_result_id = result.id,
                station_id        = s.id,
                station_order     = s.station_order,
                time_s            = time_s,
                reps_completed    = reps,
                effort            = effort,
                skipped           = skipped,
                notes             = snotes,
            ))

        db.session.commit()
        return _htmx_or_redirect(url_for('premade.view', pw_id=pw_id))

    last_result = (PremadeResult.query
                   .filter_by(premade_workout_id=pw_id)
                   .order_by(PremadeResult.done_at.desc())
                   .first())
    last_times = {}
    if last_result:
        for sr in last_result.station_results.all():
            last_times[sr.station_id] = _fmt_time(sr.time_s)

    return render_template('premade/log.html', pw=pw, stations=stations,
                           weight_unit=session.get('weight_unit', 'lbs'),
                           last_result=last_result, last_times=last_times)


@premade_bp.route('/data/<int:pw_id>')
def chart_data(pw_id):
    pw       = PremadeWorkout.query.get_or_404(pw_id)
    stations = pw.stations.order_by(PremadeStation.station_order).all()
    results  = (PremadeResult.query
                .filter_by(premade_workout_id=pw_id)
                .order_by(PremadeResult.done_at.asc()).all())

    station_list = [{'id': s.id, 'name': s.name, 'order': s.station_order} for s in stations]

    result_list = []
    for r in results:
        splits = {
            str(sr.station_id): {'time_s': sr.time_s, 'time_fmt': _fmt_time(sr.time_s)}
            for sr in r.station_results.all()
        }
        result_list.append({
            'date':       r.done_at.strftime('%Y-%m-%d'),
            'total_s':    r.total_time_s,
            'total_fmt':  _fmt_time(r.total_time_s),
            'completed':  r.completed,
            'result_id':  r.id,
            'workout_id': r.workout_id,
            'splits':     splits,
        })

    return jsonify({'stations': station_list, 'results': result_list})