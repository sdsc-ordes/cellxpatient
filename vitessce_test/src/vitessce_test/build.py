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

from vitessce_test.datasets import prepare_datasets
from vitessce_test.settings import DATA_DIR, DATA_URL

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


def save_config(
    config_dict: dict[str, Any],
    template_path: Path
) -> Path:

    config_path = template_path.parent / (template_path.stem.replace("_template", "") + "_view.json")
    with open(config_path, "w") as f:
        json.dump(config_dict, f, indent=2)
    return config_path


def add_view(
    vc: VitessceConfig,
    dataset: VitessceConfigDataset,
    view_name: str,
    grid: list[int],
    props: dict[str, Any] | None = None,
) -> VitessceConfigView:
    x, y, w, h = grid
    if view_name == "scatterplot":
        view = vc.add_view(                         # pyright: ignore[reportUnknownMemberType]
            VIEW_MAPPING[view_name],
            dataset=dataset,
            mapping="UMAP",
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
                _ = view.use_coordination(scope)                                      # pyright: ignore[reportUnknownMemberType]

    # Add specific layer coordination spaces for each spatial dataset
    # (required by spatial and layer controller views)
    if "per_layer" in coordination_space:
        for dataset in datasets:
            dataset_uid : str = vitessce_datasets[dataset].get_uid()                  # pyright: ignore[reportAssignmentType, reportUnknownVariableType]

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


def build_config(
    template_path: Path
) -> Path:

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
    vitessce_datasets = prepare_datasets(vc, datasets)

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
                grid_offset = datasets[vitessce_dataset_name].get("grid_offset_xy", [0, 0])
            else:
                grid = views[view]["datasets"][vitessce_dataset_name]["grid_xywh"]
                grid_offset = [0, 0]

            views_per_dataset[vitessce_dataset_name][view] = add_view(
                vc,
                vitessce_dataset,
                view_name=view,
                grid=[grid[0] + grid_offset[0], grid[1] + grid_offset[1], grid[2], grid[3]],
                props=views[view].get("props", None),
            )

    # Coordinate views across datasets
    coordination_scopes: dict[str, dict[str, Any]] = {}
    for space_name, coordination_space in template["coordination"].items():
        coordination_scopes[space_name] = add_coordination_space(vc, coordination_space, views_per_dataset, vitessce_datasets)

    config_dict = vc.to_dict(base_url=DATA_URL)                    # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    config_path = save_config(config_dict, template_path)          # pyright: ignore[reportUnknownArgumentType]

    return config_path
