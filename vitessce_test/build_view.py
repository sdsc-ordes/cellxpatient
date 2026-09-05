import json
from pathlib import Path
import anndata as ad

from vitessce import (
    VitessceConfig,
    Component as cm,
    CoordinationType as ct,
    AnnDataWrapper,
)
from typing import Any

PORT = 8008
BASE_URL = f"http://localhost:{PORT}"
DATA_DIR = Path(".", "data", "Dunlap_2022")

VIEW_MAPPING = {
    "scatterplot": cm.SCATTERPLOT,
    "heatmap": cm.HEATMAP,
    "violin": cm.OBS_SET_FEATURE_VALUE_DISTRIBUTION,
    "obs_sets": cm.OBS_SETS,
    "obs_set_sizes": cm.OBS_SET_SIZES,
    "description": cm.DESCRIPTION,
}

GRID = {
    "description": (0, 0, 6, 2),
    "scatterplot": (0, 2, 6, 4),
    "obs_sets": (0, 6, 3, 4),
    "obs_set_sizes": (3, 6, 3, 4),
    "heatmap": (0, 10, 6, 4),
    "violin": (0, 14, 6, 4),
}


def prepare_subset(
    adata: ad.AnnData,
    source_path: Path,
    condition_col: str,
    condition_name: str,
    obs_cols: list[str],
) -> tuple[Path, dict[str, list[str]]]:
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

    obs_values = {
        obs_col: (
            subset.obs[obs_col]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        for obs_col in obs_cols
    }
    return out_path, obs_values


def add_anndata_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    adata_path: Path | str,
    obs_embedding_paths: list[str] = ["obsm/X_umap"],
    obs_embedding_names: list[str] = ["UMAP"],
    obs_set_paths: list[str] = ["obs/pred_cell_type"],
    obs_set_names: list[str] = ["Cell Type"],
    obs_feature_matrix_path: str = "X",
    initial_feature_filter_path: str = "var/highly_variable"
):

    # Add datasets to the widget (dataset = container for file per data type)
    dataset = vc.add_dataset(
        name=dataset_name)

    # Use AnnDataWrapper to automatically handle pahts to relevant data
    dataset.add_object(
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


def add_list_views(
    vc: VitessceConfig,
    dataset: Any,
    list_view_names: list[cm],
    grid_indent: int,
    mapping: str | None = None
) -> dict[cm, Any]:
    views = {}
    for name in list_view_names:
        x, y, w, h = GRID[name]
        x = x + grid_indent
        if name == "scatterplot" and mapping is not None:
            views[name] = vc.add_view(
                VIEW_MAPPING[name],
                dataset=dataset,
                mapping=mapping,
            ).set_xywh(x, y, w, h)

        else:
            views[name] = vc.add_view(
                VIEW_MAPPING[name],
                dataset=dataset,
            ).set_xywh(x, y, w, h)

    return views


def link_subset_views(
    vc: VitessceConfig,
    views: dict[cm, Any],
    view_to_link_names: list[str],
    locally_coord_types: list[Any],
    locally_coord_initial_values: list[list[str] | None],
) -> None:

    views_to_link = [views[view_name] for view_name in view_to_link_names]

    vc.link_views(
        views_to_link,
        locally_coord_types,
        locally_coord_initial_values,
    )


def main():

    # Instantiate the Vitessce widget configuration
    vc = VitessceConfig(
        schema_version="1.0.15",
        name="Dunlap 2022",
        description="Comparison of gene expression between Healthy and SLE scRNA-seq data",
        base_dir=DATA_DIR)

    # Extract two sub AnnData objects
    adata_path = Path(DATA_DIR, "Dunlap_2022_corrected.zarr")
    adata = ad.read_zarr(
        adata_path)

    subsets = ["Healthy", "Systemic Lupus Erythematosus"]
    views_per_subset = {}
    grid_indent = 0
    for subset in subsets:

        subset_path, obs_lists = prepare_subset(
            adata,
            adata_path,
            "Disease",
            subset,
            ["pred_cell_type_filtered"]
        )
        dataset = add_anndata_dataset(
            vc,
            f"scRNA-seq - {subset}",
            subset_path.relative_to(DATA_DIR),
            obs_set_paths = ["obs/pred_cell_type_filtered"],

        )

        # Add views for current subset
        views_to_add = list(VIEW_MAPPING.keys())
        views_per_subset[subset] = add_list_views(
            vc,
            dataset,
            views_to_add,
            grid_indent,
            mapping="UMAP",
        )

        # Set specific view properties
        views_per_subset[subset]["heatmap"].set_props(transpose=True)
        views_per_subset[subset]["description"].set_props(description=f"scRNA-seq from {subset.lower()} donors")

        # Define per condition coordination scope
        view_to_link_names = [
            "scatterplot", "obs_sets", "obs_set_sizes", "heatmap", "violin"]
        locally_coord_types = [
            ct.OBS_TYPE,
            ct.OBS_SET_SELECTION,
            ct.OBS_HIGHLIGHT
        ]
        locally_coord_initial_values = [
            "cell",
            [["Cell Type", cell_type] for cell_type in obs_lists["pred_cell_type_filtered"]],
            None,
        ]
        link_subset_views(
            vc,
            views_per_subset[subset],
            view_to_link_names,
            locally_coord_types,
            locally_coord_initial_values,
        )

        grid_indent += 6

    # Define global coordination scope for Heatmap and Violin plots
    plots = ["heatmap", "violin"]
    view_to_link = [views_per_subset[subset][plot] for subset in views_per_subset for plot in plots]
    global_coord_types = [
        ct.FEATURE_TYPE,
        ct.FEATURE_VALUE_TYPE,
        ct.FEATURE_HIGHLIGHT,
        ct.FEATURE_SELECTION,
    ]
    global_coord_initial_values = [
        "gene",
        "expression",
        None,
        ["FXYD3"],
    ]
    vc.link_views(
        view_to_link,
        global_coord_types,
        global_coord_initial_values,
    )



    config_dict = vc.to_dict(base_url=BASE_URL)
    config_json_filename = Path(DATA_DIR, "dunlap_2022_healthy_x_sle_view.json")
    with open(config_json_filename, "w") as f:
        json.dump(config_dict, f, indent=4)
    vc.web_app(port=BASE_URL[-4:])

if __name__ == "__main__":
    main()
