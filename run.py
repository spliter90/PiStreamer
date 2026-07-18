from waitress import serve
from pistreamer.app import app, config

if __name__ == "__main__":
    serve(app, host=config["web"]["host"], port=int(config["web"]["port"]), threads=4)
