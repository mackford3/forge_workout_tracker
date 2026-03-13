import os
from flask import Flask, session
from .models import db


def create_app():
    app = Flask(__name__)

    db_user   = os.environ.get('DB_USER',   'postgres')
    db_pass   = os.environ.get('DB_PASS',   '')
    db_host   = os.environ.get('DB_HOST',   'localhost')
    db_port   = os.environ.get('DB_PORT',   '5432')
    db_name   = os.environ.get('DB_NAME',   'forge_workouts')
    db_schema = os.environ.get('DB_SCHEMA', 'forge')

    # Strip any accidental whitespace from env values
    db_user   = db_user.strip()
    db_pass   = db_pass.strip()
    db_host   = db_host.strip()
    db_port   = db_port.strip()
    db_name   = db_name.strip()
    db_schema = db_schema.strip()

    # Validate port is a number before SQLAlchemy tries to parse it
    if not db_port.isdigit():
        raise ValueError(
            f"DB_PORT must be a number, got: '{db_port}'. "
            f"Check your .env file — each variable must be on its own line."
        )

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
    from .routes.workouts  import workouts_bp
    from .routes.progress  import progress_bp
    from .routes.plans import plans_bp
    from .routes.exercises import exercises_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(workouts_bp,  url_prefix='/workouts')
    app.register_blueprint(progress_bp,  url_prefix='/progress')
    app.register_blueprint(plans_bp, url_prefix='/plans')
    app.register_blueprint(exercises_bp, url_prefix='/exercises')

    @app.context_processor
    def inject_globals():
        unit = session.get('weight_unit', app.config['WEIGHT_UNIT'])
        return {'weight_unit': unit}

    return app