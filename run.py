from waitress import serve
from pistreamer.app import app, config
import pistreamer.settings_pages  # noqa: F401
import pistreamer.network  # noqa: F401
import pistreamer.updater  # noqa: F401
import pistreamer.diagnostics  # noqa: F401

if __name__ == "__main__":
    serve(app, host=config["web"]["host"], port=int(config["web"]["port"]), threads=4)
