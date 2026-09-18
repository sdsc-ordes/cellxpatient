import json
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from vitessce_test.settings import DATA_DIR, DATA_URL, FRONTEND_DIR, HOST

DEFAULT_HEIGHT = None

def load_config(
    config_path: Path,
) -> dict[str, Any]:

    with open(config_path) as f:
        return json.load(f)


def create_app(
    config_dict: dict[str, Any],
) -> FastAPI:
    app = FastAPI()

    app_height = config_dict.get("app", {}).get("height", DEFAULT_HEIGHT)

    @app.get("/api/config")
    def get_config():
        return {
            "config": config_dict,
            "height": app_height,
        }

    # Serve data files.
    app.mount(
        DATA_URL,
        StaticFiles(directory=DATA_DIR),
        name="data",
    )

    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="frontend",
    )

    return app


def serve_config(
    config_path: Path,
    port: int,
) -> None:

    config_dict = load_config(config_path)

    app = create_app(config_dict)
    uvicorn.run(
        app,
        host=HOST,
        port=port,
    )
