import copy
import json
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from vitessce_test.settings import DATA_DIR, DATA_URL, FRONTEND_DIR, HOST


def load_config(
    config_path: Path,
) -> dict[str, Any]:

    with open(config_path) as f:
        return json.load(f)


def set_base_url(
    config_dict: dict[str, Any],
    base_url: str,
) -> dict[str, Any]:

    config = copy.deepcopy(config_dict)
    for dataset in config["datasets"]:
        for file in dataset["files"]:
            relative_url = file["url"]
            if relative_url and not relative_url.startswith(("http://", "https://")):
                url = base_url.rstrip("/") + "/" + relative_url.lstrip("/")
            else:
                url = relative_url
            file["url"] = url
    return config


def create_app(
    config_dict: dict[str, Any],
) -> FastAPI:
    app = FastAPI()

    @app.get("/api/config")
    def get_config(request: Request):
        return set_base_url(config_dict, str(request.base_url))

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
