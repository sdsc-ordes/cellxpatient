import copy
import json
from pathlib import Path
from typing import Any

import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from vitessce_test.settings import DATA_DIR, DATA_URL, FRONTEND_DIR, HOST

DEFAULT_HEIGHT = None

# Custom comparison column, generated on the fly from the groups built in the UI.
# Keep these values in sync with frontend/src/customGroups.js.
CUSTOM_SET_NAME = "Custom comparison"
CUSTOM_COLUMN = "__custom_comparison__"
GROUP_LABELS = {"A": "Group A", "B": "Group B"}
OTHER_LABEL = "Other"
SAMPLES_ENDPOINT = "/api/samples.csv"


def load_config(
    config_path: Path,
) -> dict[str, Any]:

    with open(config_path) as f:
        return json.load(f)


def resolve_data_path(url: str) -> Path:
    prefix = DATA_URL.rstrip("/") + "/"
    if not url.startswith(prefix):
        raise ValueError(f"Sample sets URL {url!r} is not served under {DATA_URL!r}")
    return Path(DATA_DIR) / url[len(prefix):]


def prepare_custom_groups(
    config_dict: dict[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame, dict[str, str]]:
    config = copy.deepcopy(config_dict)

    for dataset in config.get("datasets", []):
        for file in dataset.get("files", []):
            if file.get("fileType") != "sampleSets.csv":
                continue

            options = file.setdefault("options", {})
            sample_sets = options.get("sampleSets", [])

            samples = pd.read_csv(
                resolve_data_path(file["url"]),
                dtype=str,
                keep_default_na=False,
            )

            name_to_column = {entry["name"]: entry["column"] for entry in sample_sets}

            options["sampleSets"] = [
                *sample_sets,
                {"name": CUSTOM_SET_NAME, "column": CUSTOM_COLUMN},
            ]
            file["url"] = SAMPLES_ENDPOINT

            return config, samples, name_to_column

    raise ValueError("The config has no sampleSets.csv file.")


def match_samples(
    samples: pd.DataFrame,
    name_to_column: dict[str, str],
    criteria: dict[str, list[str]],
) -> pd.Series:

    active = {name: values for name, values in criteria.items() if values}

    if not active:
        return pd.Series(False, index=samples.index)

    mask = pd.Series(True, index=samples.index)

    for set_name, values in active.items():
        column = name_to_column.get(set_name)
        if column is None:
            raise HTTPException(400, f"Unknown sample category: {set_name!r}")
        mask &= samples[column].isin([str(v) for v in values])

    return mask


def create_app(
    config_dict: dict[str, Any],
) -> FastAPI:
    app = FastAPI()

    app_height = config_dict.get("app", {}).get("height", DEFAULT_HEIGHT)
    served_config, samples, name_to_column = prepare_custom_groups(config_dict)

    @app.get("/api/config")
    def get_config():
        return {
            "config": served_config,
            "height": app_height,
        }

    @app.get(SAMPLES_ENDPOINT)
    def get_samples(groups: str | None = Query(None)):
        table = samples.copy()
        table[CUSTOM_COLUMN] = OTHER_LABEL

        if groups:
            try:
                parsed = json.loads(groups)
            except json.JSONDecodeError as error:
                raise HTTPException(400, f"Invalid groups parameter: {error}")

            masks = {
                key: match_samples(samples, name_to_column, parsed.get(key, {}))
                for key in GROUP_LABELS
            }

            overlap = masks["A"] & masks["B"]
            if overlap.any():
                raise HTTPException(
                    400,
                    f"Groups overlap on {int(overlap.sum())} sample(s).",
                )

            for key, label in GROUP_LABELS.items():
                table.loc[masks[key], CUSTOM_COLUMN] = label

        return Response(
            table.to_csv(index=False),
            media_type="text/csv",
        )

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
