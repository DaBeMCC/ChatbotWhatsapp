import atexit
import logging
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)


def create_app() -> Flask:
    app = Flask(__name__)

    from config import Config
    app.config['SECRET_KEY'] = Config.SECRET_KEY

    from models import database, crear_tablas
    crear_tablas()

    @app.before_request
    def _db_connect():
        database.connect(reuse_if_open=True)

    @app.teardown_request
    def _db_close(exc):
        if not database.is_closed():
            database.close()

    from routes.auth import auth_bp
    from routes.taller import taller_bp
    from routes.marketing import marketing_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(taller_bp)
    app.register_blueprint(marketing_bp)

    from scheduler import iniciar_scheduler
    scheduler = iniciar_scheduler()
    atexit.register(lambda: scheduler.shutdown(wait=False))

    return app


if __name__ == '__main__':
    flask_app = create_app()
    flask_app.run(debug=False, host='0.0.0.0', port=5000)
