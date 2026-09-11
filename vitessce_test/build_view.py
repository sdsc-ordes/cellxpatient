import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from vitessce import Component as cm
from vitessce import (
    CoordinationLevel as CL,
)
from vitessce import (
    VitessceConfig,
    get_initial_coordination_scope_prefix,  # pyright: ignore[reportUnknownVariableType]
)
from vitessce.config import (
    VitessceConfigCoordinationScope,
    VitessceConfigDataset,
    VitessceConfigView,
)

from datasets import prepare_datasets

PORT = 8008
BASE_URL = f"http://localhost:{PORT}"
DATA_DIR = Path(".", "data")

VIEW_MAPPING = {
    "scatterplot": cm.SCATTERPLOT,
    "heatmap": cm.HEATMAP,
    "violin": cm.OBS_SET_FEATURE_VALUE_DISTRIBUTION,
    "obs_sets": cm.OBS_SETS,
    "obs_sets_sizes": cm.OBS_SET_SIZES,
    "description": cm.DESCRIPTION,
    "feature_list": cm.FEATURE_LIST,
    "spatial": "spatialBeta",
    "layer_controller": "layerControllerBeta",
    "status": cm.STATUS,
}


def load_template(
    path: Path,
) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def update_template(
    template: dict[str, Any],
    template_path: Path,
) -> None:
    with open(template_path, "w") as f:
        yaml.safe_dump(template, f)


def add_view(
    vc: VitessceConfig,
    dataset: VitessceConfigDataset,
    view_name: str,
    grid_offset: list[int],
    grid: list[int],
    props: dict[str, Any] | None = None,
    mapping: str = "UMAP"
) -> VitessceConfigView:
    x, y, w, h = grid
    x = x + grid_offset[0]
    y = y + grid_offset[1]
    if view_name == "scatterplot":
        view = vc.add_view(                         # pyright: ignore[reportUnknownMemberType]
            VIEW_MAPPING[view_name],
            dataset=dataset,
            mapping=mapping,
        ).set_xywh(x, y, w, h)

    else:
        view = vc.add_view(                         # pyright: ignore[reportUnknownMemberType]
            VIEW_MAPPING[view_name],
            dataset=dataset,
        ).set_xywh(x, y, w, h)

    if props is not None:
        view = view.set_props(**props)              # pyright: ignore[reportUnknownMemberType]

    return view


def add_image_layer_coordination(
    vc: VitessceConfig,
    views: list[VitessceConfigView],
    values: str,
) -> None:
    _ = vc.link_views_by_dict(                              # pyright: ignore[reportUnknownMemberType]
        views,
        {
            "imageLayer": CL([
                values
            ])
        },
        scope_prefix=get_initial_coordination_scope_prefix(
            "A",
            "image",
        ),
    )


def add_segmentation_layer_coordination(
    vc: VitessceConfig,
    dataset_uid: str,
    views: list[VitessceConfigView],
    layers_data: dict[str, Any],
) -> None:
    layers = [
        {
            "fileUid": channel.replace("_channel", ""),
            "segmentationChannel": CL([
                layers_data[channel]
            ]),
        } for channel in layers_data
    ]
    if not layers:
        return
    _ = vc.link_views_by_dict(                              # pyright: ignore[reportUnknownMemberType]
        views,
        {
            "segmentationLayer": CL([*layers])
        },
        scope_prefix=get_initial_coordination_scope_prefix(
            dataset_uid,
            "obsSegmentations",
        ),
    )


def resolve_layer_values(
    layer: dict[str, Any],
    scopes: dict[str, Any]
) -> dict[str, Any]:

    values = layer.get("values", {})
    inherit = layer.get("inherit", False)
    inherit_values = layer.get("inherit_values", {})

    if not inherit and not inherit_values:
        return dict(values)
    else:
        if inherit_values:
            return {
                **values,
                **{k: v for k, v in scopes.items() if k in inherit_values}
            }
        return {
            **values,
            **scopes
        }


def add_coordination_space(
    vc: VitessceConfig,
    coordination_space: dict[str, Any],
    views: dict[str, dict[str, VitessceConfigView]],
    vitessce_datasets: dict[str, VitessceConfigDataset],
) -> dict[str, VitessceConfigCoordinationScope]:

    # Define views to link per dataset
    datasets = coordination_space["datasets"]
    view_to_link_names = coordination_space["views"]

    scopes: dict[str, VitessceConfigCoordinationScope] = {}

    # Keep track of the created coordination scopes
    for coord_name, initial_value in coordination_space["values"].items():
        scope: VitessceConfigCoordinationScope = vc.add_coordination(coord_name)[0]   # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        _ = scope.set_value(initial_value)                                            # pyright: ignore[reportUnknownMemberType]
        scopes[coord_name] = scope

        for dataset in datasets:
            for view_name in view_to_link_names:
                view = views[dataset][view_name]
                _ = view.use_coordination(scope)           # pyright: ignore[reportUnknownMemberType]

    # Add specific layer coordination spaces for each spatial dataset (required by spatial and layer controller
    # views)
    if "per_layer" in coordination_space:
        for dataset in datasets:
            dataset_uid : str = vitessce_datasets[dataset].get_uid()                # pyright: ignore[reportAssignmentType, reportUnknownVariableType]

            for layer_name, layer_data in coordination_space["per_layer"].items():
                view_to_link_names = layer_data["views"]
                views_to_link = [views[dataset][view_name]
                    for view_name in view_to_link_names]
                if layer_name == "image_layer":
                    add_image_layer_coordination(vc, views_to_link, layer_data["values"])
                if layer_name == "segmentation_layer":
                    layers = {
                        channel : resolve_layer_values(
                            layer_data[channel],
                            scopes
                        ) for channel in ["cell_channel", "nucleus_channel"] if channel in layer_data
                    }
                    add_segmentation_layer_coordination(vc, dataset_uid, views_to_link, layers)
    return scopes


def build_view(
    template_path: Path
) -> dict[str, Any]:

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    template = load_template(template_path)

    # Instantiate the Vitessce widget configuration
    vc = VitessceConfig(
        schema_version="1.0.17",
        name=template["name"],
        description=template["description"],
        base_dir=DATA_DIR)

    # Add to vitessce config all datasets to display
    datasets = template["datasets"]
    vitessce_datasets, template_changed = prepare_datasets(vc, datasets)

    # Update template if datasets changed
    if template_changed:
        update_template(template, template_path)

    # Add views to vitessce config
    views = template["views"]
    views_per_dataset: dict[str, dict[str, VitessceConfigView]] = {}
    for vitessce_dataset_name, vitessce_dataset in vitessce_datasets.items():
        views_to_add = [view_name for view_name in views if vitessce_dataset_name in views[view_name]["datasets"]]
        views_per_dataset[vitessce_dataset_name] = {}
        for view in views_to_add:
            if "grid_xywh" not in views[view] and "grid_xywh" not in views[view]["datasets"][vitessce_dataset_name]:
                raise ValueError(f"Grid indent not found for view {view} and dataset {vitessce_dataset_name}")
            if "grid_xywh" in views[view]:
                grid = views[view]["grid_xywh"]
                grid_offset = views[view]["datasets"][vitessce_dataset_name].get("grid_offset_xy", [0, 0])
            else:
                grid = views[view]["datasets"][vitessce_dataset_name]["grid_xywh"]
                grid_offset = [0, 0]

            views_per_dataset[vitessce_dataset_name][view] = add_view(
                vc,
                vitessce_dataset,
                view_name=view,
                grid=grid,
                grid_offset=grid_offset,
                props=views[view].get("props", None),
            )

    # Coordinate views across datasets
    coordination_scopes: dict[str, dict[str, Any]] = {}
    for space_name, coordination_space in template["coordination"].items():
        coordination_scopes[space_name] = add_coordination_space(vc, coordination_space, views_per_dataset, vitessce_datasets)

    launch_app(vc)
    return vc.to_dict(base_url=BASE_URL)                    # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]


def serve_view(config_path: Path) -> None:
    with open(config_path) as f:
        config = json.load(f)
    vc = VitessceConfig.from_dict(config=config)           # pyright: ignore[reportUnknownMemberType]
    launch_app(vc)


def launch_app(
    vc: VitessceConfig
) -> None:
    _ = vc.web_app(port=PORT)                               # pyright: ignore[reportUnknownMemberType]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a Vitessce config view from a YAML template or "
            "render a Vitessce config view from a JSON view file."
        )
    )
    _ = parser.add_argument(
        "--template",
        default=None,
        type=str,
        help="Path to the Vitessce view YAML template.",
    )
    _ = parser.add_argument(
        "--config",
        default=None,
        type=str,
        help="Path to the Vitessce view JSON config.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.config is not None and args.template is not None:
        raise ValueError("Cannot specify both --config and --template.")

    if args.config is not None:
        config_path = Path(args.config)
        serve_view(config_path)

    if args.template is not None:
        template_path = Path(args.template)
        config_dict = build_view(template_path)

        config_json_filename = template_path.with_name(
            template_path.stem.replace("template", "view") + ".json"
        )

        with open(config_json_filename, "w") as f:
            json.dump(config_dict, f, indent=4)
