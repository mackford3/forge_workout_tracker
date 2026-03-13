import os
from flask import Flask, session
from .models import db


def create_app():
    app = Flask(__name__)

    db_user   = os.environ.get('DB_USER')
    db_pass   = os.environ.get('DB_PASS')
    db_host   = os.environ.get('DB_HOST')
    db_port   = os.environ.get('DB_PORT')
    db_name   = os.environ.get('DB_NAME')
    db_schema = os.environ.get('DB_SCHEMA')

    db_url = f'postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {
            'options': f'-csearch_path={db_schema}'
        }
    }
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
    app.config['WEIGHT_UNIT'] = os.environ.get('WEIGHT_UNIT', 'lbs')

    db.init_app(app)

    from .routes.main import main_bp
    from .routes.workouts import workouts_bp
    from .routes.plans import plans_bp
    from .routes.exercises import exercises_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(workouts_bp, url_prefix='/workouts')
    app.register_blueprint(plans_bp, url_prefix='/plans')
    app.register_blueprint(exercises_bp, url_prefix='/exercises')

    @app.context_processor
    def inject_globals():
        unit = session.get('weight_unit', app.config['WEIGHT_UNIT'])
        return {'weight_unit': unit}

    return app