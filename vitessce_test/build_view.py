import argparse
import json
from pathlib import Path
from this import s
from turtle import st
from typing import Any

import anndata as ad
from numba.cuda.stubs import shared
import pandas as pd
import numpy as np
from spatialdata_io import xenium
from vitessce import (
    AnnDataWrapper,
    CoordinationLevel as CL,
    SpatialDataWrapper,
    VitessceConfig,
    get_initial_coordination_scope_prefix,
)
from vitessce import Component as cm
from vitessce import CoordinationType as ct
from vitessce.config import (
    VitessceConfigDataset,
    VitessceConfigView,
    VitessceConfigCoordinationScope,
)
import yaml

PORT = 8008
BASE_URL = f"http://localhost:{PORT}"
DATA_DIR = Path(".", "data", "Dunlap_2022")

DEFAULT_EMBEDDING_PATH = "obsm/X_umap"
DEFAULT_EMBEDDING_NAME = "UMAP"
DEFAULT_FEATURE_MATRIX_PATH = "X"
DEFAULT_OBS_SET_PATH = "obs/pred_cell_type"
DEFAULT_OBS_SET_NAME = "Cell Type"
DEFAULT_FEATURE_FILTER_PATH = "var/highly_variable"

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

COORDINATION_MAPPING = {
    "obsType": ct.OBS_TYPE,
    "obsSetSelection": ct.OBS_SET_SELECTION,
    "obsHighlight": ct.OBS_HIGHLIGHT,
    "featureType": ct.FEATURE_TYPE,
    "featureValueType": ct.FEATURE_VALUE_TYPE,
    "featureHighlight": ct.FEATURE_HIGHLIGHT,
    "featureSelection": ct.FEATURE_SELECTION,
    "obsColorEncoding": ct.OBS_COLOR_ENCODING,
    "featureValueColormapRange": ct.FEATURE_VALUE_COLORMAP_RANGE,
    "spatialLayerColormap": "spatialLayerColormap",
}


def load_template(
    path: Path,
) -> dict[str, Any]:
    with open(path) as f:
        return yaml.safe_load(f)


def prepare_subset(
    adata: ad.AnnData,
    source_path: Path,
    condition_col: str,
    condition_name: str
) -> Path:
    """
    Prepare a subset of the AnnData object based on the condition column and name.
    """
    out_path = Path(
        source_path.parent,
        f"{source_path.stem}_{condition_name.lower().replace(' ', '_')}.zarr"
    )
    mask = adata.obs[condition_col] == condition_name
    subset: ad.Anndata = adata[mask]
    if not out_path.exists():
        subset.write_zarr(
            store=out_path
        )
    return out_path


def add_anndata_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    adata_path: Path | str,
    obs_embedding_paths: list[str] | None = None,
    obs_embedding_names: list[str] | None = None,
    obs_set_paths: list[str] | None = None,
    obs_set_names: list[str] | None = None,
    obs_feature_matrix_path: str = DEFAULT_FEATURE_MATRIX_PATH,
    initial_feature_filter_path: str = DEFAULT_FEATURE_FILTER_PATH
) -> VitessceConfigDataset:
    obs_embedding_paths = obs_embedding_paths or [DEFAULT_EMBEDDING_PATH]
    obs_embedding_names = obs_embedding_names or [DEFAULT_EMBEDDING_NAME]
    obs_set_paths = obs_set_paths or [DEFAULT_OBS_SET_PATH]
    obs_set_names = obs_set_names or [DEFAULT_OBS_SET_NAME]

    # Add datasets to the widget (dataset = container for file per data type)
    dataset = vc.add_dataset(                       # pyright: ignore[reportUnknownMemberType]
        name=dataset_name)

    # Use AnnDataWrapper to automatically handle pahts to relevant data
    _ = dataset.add_object(                         # pyright: ignore[reportUnknownMemberType]
        AnnDataWrapper(
            adata_path=adata_path,
            obs_embedding_paths=obs_embedding_paths,
            obs_embedding_names=obs_embedding_names,
            obs_set_paths=obs_set_paths,
            obs_set_names=obs_set_names,
            obs_feature_matrix_path=obs_feature_matrix_path,
            initial_feature_filter_path=initial_feature_filter_path
        )
    )
    return dataset


def prepare_anndata_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    dataset: dict[str, Any]
) -> dict[str,VitessceConfigDataset]:

    adata_path = Path(DATA_DIR, dataset["dataset_path"])
    adata = ad.read_zarr(                                   # pyright: ignore[reportUnknownMemberType]
        adata_path)

    datasets: dict[str, tuple[str, Path]] = {}
    if dataset['subsets_only'] and 'subsets' not in dataset:
        raise ValueError("subsets_only set to True but no subsets defined")
    if not dataset['subsets_only']:
        datasets[dataset_name] = dataset_name, adata_path
    if 'subsets' in dataset:
        subsets = dataset["subsets"]
        for subset_id, subset in subsets.items():
            subset_path = prepare_subset(
                adata,
                adata_path,
                subset["column"],
                subset["value"]
            )
            datasets[subset_id] = f"{dataset_name.capitalize()} - {subset['value']}", subset_path

    vitessce_datasets: dict[str, VitessceConfigDataset] = {}
    for dataset_id, dataset_data in datasets.items():
        vitessce_datasets[dataset_id] = add_anndata_dataset(
            vc,
            dataset_data[0],
            dataset_data[1].relative_to(DATA_DIR),
            obs_set_paths = dataset["data"].get("obs_sets_paths", None),
            obs_set_names = dataset["data"].get("obs_sets_names", None),
            obs_embedding_paths=dataset["data"].get("obs_embedding_paths", None),
            obs_embedding_names=dataset["data"].get("obs_embedding_names", None),
            obs_feature_matrix_path=dataset["data"].get("feature_matrix_path", DEFAULT_FEATURE_MATRIX_PATH),
            initial_feature_filter_path=dataset["data"].get("feature_filter_path", DEFAULT_FEATURE_FILTER_PATH)
        )
    return vitessce_datasets


def add_spatial_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    dataset: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, VitessceConfigDataset]:

    options = dataset.get("data", {})
    spatialzarr_path = Path(DATA_DIR, dataset["dataset_path"])
    image_path = "images/morphology_focus"
    obs_embedding_paths = options.get("obs_embedding_paths", ["tables/table/obsm/X_umap"])
    obs_embedding_names = options.get("obs_embedding_names", ["UMAP"])
    obs_sets_paths = options.get("obs_sets_paths", ["tables/table/obs/pred_cell_type"])
    obs_sets_names = options.get("obs_sets_names", ["Cell Type"])
    obs_seg_paths = options.get("obs_seg_paths", ["shapes/cell_boundaries"])
    obs_feature_matrix_path = options.get("obs_feature_matrix_path", "tables/table/X")
    obs_points_path = options.get("obs_points_path", "points/transcripts")
    obs_points_feature_index_column = options.get("obs_points_feature_index_column", "codeword_index")
    obs_points_morton_code_column = options.get("obs_points_morton_code_column", "morton_code_2d")
    #obs_spots_path = options.get("obs_spots_path", "shapes/cell_circles")

    # Add datasets to the widget (dataset = container for file per data type)
    vitessce_dataset = vc.add_dataset(                        # pyright: ignore[reportUnknownMemberType]
        name=dataset_name)

    _ = vitessce_dataset.add_object(                          # pyright: ignore[reportUnknownMemberType]
        SpatialDataWrapper(
            sdata_path=str(spatialzarr_path.relative_to(DATA_DIR)),
            image_path=image_path,
            obs_embedding_paths=obs_embedding_paths,
            obs_embedding_names=obs_embedding_names,
            obs_set_paths=obs_sets_paths,
            obs_set_names=obs_sets_names,
            obs_feature_matrix_path=obs_feature_matrix_path,
            #obs_points_path=obs_points_path,
            #obs_points_feature_index_column=obs_points_feature_index_column,
            #obs_points_morton_code_column=obs_points_morton_code_column,
            #obs_spots_path=obs_spots_path,
            #obs_segmentations_path=obs_seg_path,
            coordination_values={
                "obsType": "cell",
                "featureType": "gene",
                "featureValueType": "expression",
            }
        )
    )

    for seg_path in obs_seg_paths:
        url = f"{BASE_URL}/{spatialzarr_path.relative_to(DATA_DIR).as_posix()}"
        if 'cell' in seg_path:
            seg_type = "cell"
        elif 'nucleus' in seg_path:
            seg_type = "nucleus"
        else:
            seg_type = "cell"
        _ = vitessce_dataset.add_file(                          # pyright: ignore[reportUnknownMemberType]
            file_type = "shapes.spatialdata.zarr",
            url=url,
            coordination_values={
                "obsType": seg_type,
                "fileUid": seg_type
            },
            options={
                "path": seg_path,
                "tablePath": "tables/table",
                "region": "cell_boundaries"
            }
        )
    return { dataset_name: vitessce_dataset }


def prepare_spatial_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    dataset: dict[str, Any],
) -> dict[str, VitessceConfigDataset]:

    dataset_path = Path(DATA_DIR, dataset["dataset_path"])
    if not dataset.get("is_preprocessed", False) and not dataset_path.with_suffix(".zarr").exists():
        sdata = xenium(dataset_path)
        adata = sdata.tables["table"]
        umap_data = pd.read_csv(dataset_path / "analysis" / "umap" / "gene_expression_2_components" / "projection.csv", index_col=0)
        umap_data_full = pd.DataFrame(index=adata.obs["cell_id"])
        umap_data_full.loc[umap_data.index, ["UMAP-1", "UMAP-2"]] = umap_data.loc[umap_data.index, ["UMAP-1", "UMAP-2"]]
        adata.obsm["X_umap"] = umap_data_full.to_numpy(np.float32)
        clusters = pd.read_csv(dataset_path / "analysis" / "clustering" / "gene_expression_graphclust" / "clusters.csv", index_col=0)
        clusters_full = pd.DataFrame(index=adata.obs["cell_id"])
        clusters_full.loc[clusters.index, "Cluster"] = clusters.loc[clusters.index, "Cluster"]
        adata.obs["clusters"] = clusters_full["Cluster"]

        # Handle nullable string indexes for compatibility with older pandas versions.
        adata.var.index = pd.Index(
            adata.var.index.astype(str).to_numpy(),
            dtype=object,
        )
        adata.obs.index = pd.Index(
            adata.obs.index.astype(str).to_numpy(),
            dtype=object,
        )
        ad.settings.allow_write_nullable_strings=False

        sdata.tables["table"] = adata
        sdata.write(dataset_path.with_suffix(".zarr"))
        dataset["dataset_path"] = str(dataset_path.relative_to(DATA_DIR).with_suffix(".zarr"))

    return add_spatial_dataset(vc, dataset_name, dataset, options=dataset.get("data", {}))


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
            "A",
            "obsSegmentations",
        ),
    )


def add_coordination_space(
    vc: VitessceConfig,
    coordination_space: dict[str, Any],
    views: dict[str, dict[str, VitessceConfigView]],
) -> dict[str, VitessceConfigCoordinationScope]:

    # Define views to link per dataset
    datasets = coordination_space["datasets"]
    view_to_link_names = coordination_space["views"]

    scopes: dict[str, VitessceConfigCoordinationScope] = {}

    # Keep track of the created coordination scopes
    for coord_name, initial_value in coordination_space["values"].items():
        coord_type = COORDINATION_MAPPING[coord_name]
        scope: VitessceConfigCoordinationScope = vc.add_coordination(coord_type)[0]   # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
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
            for layer_name, layer_data in coordination_space["per_layer"].items():
                view_to_link_names = layer_data["views"]
                views_to_link = [views[dataset][view_name]
                    for view_name in view_to_link_names]
                if layer_name == "image_layer":
                    add_image_layer_coordination(vc, views_to_link, layer_data["values"])
                if layer_name == "segmentation_layer":
                    layers = {channel: None for channel in ["cell_channel", "nucleus_channel"] if channel in layer_data}
                    if not layers:
                        continue
                    for channel in layers:
                        if "from" in layer_data[channel]["values"]:
                            layers[channel] = scopes
                            layer_data[channel]["values"].pop("from")
                            layers[channel].update(layer_data[channel]["values"])
                        else:
                            layers[channel] = layer_data[channel]["values"]
                    add_segmentation_layer_coordination(vc, views_to_link, layers)
    return scopes


def build_view(
    template: dict[str, Any]
) -> dict[str, Any]:

    # Instantiate the Vitessce widget configuration
    vc = VitessceConfig(
        schema_version="1.0.17",
        name=template["name"],
        description=template["description"],
        base_dir=DATA_DIR)

    # Record all datasets to display
    datasets = template["datasets"]

    # Add datasets to vitessce config
    vitessce_datasets: dict[str, VitessceConfigDataset] = {}
    spatial_datasets: dict[str, VitessceConfigDataset] = {}
    for dataset_name, dataset in datasets.items():
        if dataset["type"] == "anndata_zarr":
            vitessce_datasets.update(prepare_anndata_dataset(vc, dataset_name, dataset))
        if dataset["type"] == "spatialdata_zarr":
            vitessce_datasets.update(prepare_spatial_dataset(vc, dataset_name, dataset))
            spatial_datasets[dataset_name] = vitessce_datasets[dataset_name]

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
        coordination_scopes[space_name] = add_coordination_space(vc, coordination_space, views_per_dataset)

    _ = vc.web_app(port=PORT)                               # pyright: ignore[reportUnknownMemberType]
    return vc.to_dict(base_url=BASE_URL)                    # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Vitessce view from a YAML template."
    )
    _ = parser.add_argument(
        "template",
        type=str,
        help="Path to the Vitessce view template.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    template_path = Path(args.template)
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    template = load_template(template_path)
    config_dict = build_view(template)

    config_json_filename = template_path.with_name(
        template_path.stem.replace("template", "view") + ".json"
    )

    with open(config_json_filename, "w") as f:
        json.dump(config_dict, f, indent=4)
