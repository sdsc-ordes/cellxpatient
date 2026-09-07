import argparse
import json
from pathlib import Path
from typing import Any

import anndata as ad
import yaml
from vitessce import AnnDataWrapper, VitessceConfig
from vitessce import Component as cm
from vitessce import CoordinationType as ct
from vitessce.config import VitessceConfigDataset, VitessceConfigView

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
}

COORDINATION_MAPPING = {
    "obsType": ct.OBS_TYPE,
    "obsSetSelection": ct.OBS_SET_SELECTION,
    "obsHighlight": ct.OBS_HIGHLIGHT,
    "featureType": ct.FEATURE_TYPE,
    "featureValueType": ct.FEATURE_VALUE_TYPE,
    "featureHighlight": ct.FEATURE_HIGHLIGHT,
    "featureSelection": ct.FEATURE_SELECTION,
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
    subset = adata[mask]
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
    dataset = vc.add_dataset(
        name=dataset_name)

    # Use AnnDataWrapper to automatically handle pahts to relevant data
    _ = dataset.add_object(
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
    dataset: dict[str, Any]
) -> dict[str,VitessceConfigDataset]:

    adata_path = Path(DATA_DIR, dataset["dataset_path"])
    adata = ad.read_zarr(
        adata_path)

    datasets = {}
    if dataset['subsets_only'] and 'subsets' not in dataset:
        raise ValueError("subsets_only set to True but no subsets defined")
    if not dataset['subsets_only']:
        datasets["A"] = dataset["dataset_name"], adata_path
    if 'subsets' in dataset:
        subsets = dataset["subsets"]
        for subset_id, subset in subsets.items():
            subset_path = prepare_subset(
                adata,
                adata_path,
                subset["column"],
                subset["value"]
            )
            datasets[subset_id] = f"{dataset['dataset_name']} - {subset['value']}", subset_path

    vitessce_datasets = {}
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
    if view_name == "scatterplot" and mapping is not None:
        view = vc.add_view(
            VIEW_MAPPING[view_name],
            dataset=dataset,
            mapping=mapping,
        ).set_xywh(x, y, w, h)

    else:
        view = vc.add_view(
            VIEW_MAPPING[view_name],
            dataset=dataset,
        ).set_xywh(x, y, w, h)

    if props is not None:
        view = view.set_props(**props)

    return view


def add_coordination_space(
    vc: VitessceConfig,
    coordination_space: dict[str, Any],
    views: dict[str, dict[str, VitessceConfigView]],
) -> None:
    # Define per condition coordination scope
    datasets = coordination_space["datasets"]
    view_to_link_names = coordination_space["views"]
    vitessce_view_to_link = [views[dataset][view_name] for dataset in datasets for view_name in view_to_link_names]
    coord_types = [COORDINATION_MAPPING[coord_type] for coord_type in coordination_space["values"]]
    coord_initial_values = [coordination_space["values"][coord_type] for coord_type in coordination_space["values"]]
    vc.link_views(
        vitessce_view_to_link,
        coord_types,
        coord_initial_values,
    )


def build_view(
    template: dict[str, Any]
) -> dict[str, Any]:

    # Instantiate the Vitessce widget configuration
    vc = VitessceConfig(
        schema_version="1.0.15",
        name=template["name"],
        description=template["description"],
        base_dir=DATA_DIR)

    # Record all datasets
    datasets = [template["datasets"][dataset] for dataset in template["datasets"]]

    # Add datasets to config
    vitessce_datasets = {}
    for dataset in datasets:
        if dataset["type"] == "anndata_zarr":
            vitessce_datasets.update(prepare_anndata_dataset(vc, dataset))

    views = template["views"]
    views_per_dataset = {}
    for vitessce_dataset_name, vitessce_dataset in vitessce_datasets.items():
        views_to_add = [view_name for view_name in views if vitessce_dataset_name in views[view_name]["datasets"]]
        views_per_dataset[vitessce_dataset_name] = {}
        for view in views_to_add:
            if "grid_xywh" not in views[view] and "grid_xywh" not in views[view]["datasets"][vitessce_dataset_name]:
                raise ValueError(f"Grid indent not found for view {view} and dataset {vitessce_dataset_name}")
            if "grid_xywh" in views[view]:
                grid = views[view]["grid_xywh"]
                grid_offset = views[view]["datasets"][vitessce_dataset_name]["grid_offset_xy"]
            else:
                grid = views[view]["datasets"][vitessce_dataset_name]["grid_xywh"]
                grid_offset = (0, 0)

            views_per_dataset[vitessce_dataset_name][view] = add_view(
                vc,
                vitessce_dataset,
                view_name=view,
                grid=grid,
                grid_offset=grid_offset,
                props=views[view].get("props", None),
            )

    coordination_spaces = [template["coordination"][space] for space in template["coordination"]]
    for coordination_space in coordination_spaces:
        add_coordination_space(vc, coordination_space, views_per_dataset)

    _ = vc.web_app(port=PORT)

    return vc.to_dict(base_url=BASE_URL)


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
