from pathlib import Path
import yaml
from typing import Any
import shutil

from scipy.sparse import csc_matrix, issparse
import anndata as ad
import numpy as np
import pandas as pd
from skimage import data
from spatialdata_io import xenium
from spatialdata import read_zarr
from vitessce import (
    AnnDataWrapper,
    SpatialDataWrapper,
    VitessceConfig,
)
from vitessce import Component as cm
from vitessce.config import (
    VitessceConfigDataset,
)

DATA_DIR = Path(".", "data")
PORT = 8008
BASE_URL = f"http://localhost:{PORT}"


ANNDATA_DEFAULTS = {
    "obs_embedding_paths": ["obsm/X_umap"],
    "obs_embedding_names": ["UMAP"],
    "obs_sets_paths": ["obs/pred_cell_type"],
    "obs_sets_names": ["Cell Type"],
    "obs_feature_matrix_path": "X",
    "initial_feature_filter_path": "var/highly_variable",
}


SPATIALDATA_DEFAULTS = {
    "image_path": "images/morphology_focus",
    "obs_feature_matrix_path": "tables/table/X",
    "obs_seg_paths": [
        "shapes/cell_boundaries",
        "shapes/nucleus_boundaries",
    ]
}


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


def update_template(
    template: dict[str, Any],
    template_path: Path,
) -> None:
    with open(template_path, "w") as f:
        yaml.safe_dump(template, f)


def get_dataset_data(
    dataset_data: dict[str, Any],
    defaults: dict[str, Any]
) -> dict[str, Any]:
    return {**defaults, **dataset_data}


def write_sparse_matrix(
    adata: ad.AnnData,
    source_path: Path,
    matrix_path: Path,
    spatial: bool = False,
) -> None:

    adata.X = csc_matrix(adata.X)                               # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]
    if spatial:
        backup_path = source_path.with_name(f"{source_path.stem}_backup.zarr")
        _ = source_path.rename(backup_path)
        sdata = read_zarr(backup_path)
        sdata.tables[matrix_path.parent.name] = adata

        # Recover backed up data if write fails
        try:
            sdata.write(source_path)
            _ = read_zarr(source_path)
        except Exception as e:
            if source_path.exists():
                shutil.rmtree(source_path)
            _ = backup_path.rename(source_path)
            raise RuntimeError(f"Failed to write sparse matrix to {source_path}: {e}")
        else:
            shutil.rmtree(backup_path)
    else:
        adata.write_zarr(store=source_path)                     # pyright: ignore[reportUnknownMemberType]


def verify_sparse_matrix(
    source_path: Path,
    matrix_path: Path,
    spatial: bool = False,
) -> None:

    adata = ad.read_zarr(Path(source_path, matrix_path.parent))     # pyright: ignore[reportUnknownMemberType]
    if not issparse(adata.X):                         # pyright: ignore[reportUnknownMemberType]
        write_sparse_matrix(
            adata,
            source_path,
            matrix_path,
            spatial
        )


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
    adata_path: Path,
    options: dict[str, Any],
) -> VitessceConfigDataset:

    # Add datasets to the widget (dataset = container for file per data type)
    dataset = vc.add_dataset(                       # pyright: ignore[reportUnknownMemberType]
        name=dataset_name)

    # If feature matrix is used, convert to CSC format
    matrix_path = options.get("obs_feature_matrix_path", None)
    if matrix_path:
        verify_sparse_matrix(
            adata_path,
            Path(matrix_path)
        )

    # Use AnnDataWrapper to automatically handle pahts to relevant data
    _ = dataset.add_object(                         # pyright: ignore[reportUnknownMemberType]
        AnnDataWrapper(
            adata_path=adata_path,
            **options
        )
    )
    return dataset


def prepare_anndata_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    template: dict[str, Any]
) -> dict[str,VitessceConfigDataset]:

    dataset = template["datasets"][dataset_name]
    adata_path = Path(DATA_DIR, dataset["dataset_path"])
    adata = ad.read_zarr(                                   # pyright: ignore[reportUnknownMemberType]
        adata_path)

    datasets: dict[str, tuple[str, Path]] = {}
    if dataset.get('subsets_only', False) and 'subsets' not in dataset:
        raise ValueError("subsets_only set to True in template but no subsets defined!")
    if not dataset.get('subsets_only', False):
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
        options = get_dataset_data(dataset.get("data", {}), ANNDATA_DEFAULTS)
        vitessce_datasets[dataset_id] = add_anndata_dataset(
            vc,
            dataset_data[0],
            dataset_data[1].relative_to(DATA_DIR),
            options
        )
    return vitessce_datasets


def prepare_xenium_dataset(
    dataset_path: Path,
    dataset: dict[str, Any],
    preprocessing_data: dict[str, Any]
) -> None:

    sdata = xenium(dataset_path)
    adata = sdata.tables["table"]

    umap_path = preprocessing_data.get("umap_path", None)
    if umap_path is not None and Path(dataset_path, umap_path).exists():
        umap_data = pd.read_csv(dataset_path / umap_path, index_col=0)
        umap_data_full = pd.DataFrame(index=adata.obs["cell_id"])
        umap_data_full.loc[umap_data.index, ["UMAP-1", "UMAP-2"]] = umap_data.loc[umap_data.index, ["UMAP-1", "UMAP-2"]]
        adata.obsm["X_umap"] = umap_data_full.to_numpy(np.float32)
        dataset["data"]["obs_embedding_paths"] = ["tables/table/obsm/X_umap"]
        dataset["data"]["obs_embedding_names"] = ["UMAP"]

    clusters_path = preprocessing_data.get("clusters_path", None)
    if clusters_path is not None and Path(dataset_path, clusters_path).exists():
        clusters = pd.read_csv(dataset_path / clusters_path, index_col=0)
        clusters_full = pd.DataFrame(index=adata.obs["cell_id"])
        clusters_full.loc[clusters.index, "Cluster"] = clusters.loc[clusters.index, "Cluster"]
        adata.obs["clusters"] = clusters_full["Cluster"]
        dataset["data"]["obs_set_paths"].append("tables/table/obs/clusters")
        dataset["data"]["obs_set_names"].append("Clusters")


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
    dataset["is_preprocessed"] = True


def add_spatial_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    dataset: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, VitessceConfigDataset]:

    spatialzarr_path = Path(DATA_DIR, dataset["dataset_path"])
    obs_seg_paths = options.pop("obs_seg_paths")

    # Verify that the feature matrix is sparse
    matrix_path = options.get("obs_feature_matrix_path", None)
    if matrix_path:
        verify_sparse_matrix(spatialzarr_path, Path(matrix_path), spatial=True)

    # Add datasets to the widget (dataset = container for file per data type)
    vitessce_dataset = vc.add_dataset(                        # pyright: ignore[reportUnknownMemberType]
        name=dataset_name)

    _ = vitessce_dataset.add_object(                          # pyright: ignore[reportUnknownMemberType]
        SpatialDataWrapper(
            sdata_path=str(spatialzarr_path.relative_to(DATA_DIR)),
            **options,
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
                "tablePath": "tables/table"
            }
        )
    return { dataset_name: vitessce_dataset }


def prepare_spatial_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    template: dict[str, Any],
    template_path: Path,
) -> dict[str, VitessceConfigDataset]:
    dataset = template["datasets"][dataset_name]
    dataset_path = Path(DATA_DIR, dataset["dataset_path"])
    if not dataset.get("is_preprocessed", False) and not dataset_path.with_suffix(".zarr").exists():
        preprocessing_data = dataset.get("preprocessing_data", {})
        if not preprocessing_data:
            raise ValueError("Preprocessing necessary but not preprocessing information provided in template.")
        spatial_type = preprocessing_data.get("spatial_type", "")
        if spatial_type == "xenium":
            prepare_xenium_dataset(dataset_path, dataset, preprocessing_data)
            update_template(template, template_path)
        else:
            raise ValueError(f"Unsupported spatial type: {spatial_type}")

    options = get_dataset_data(dataset.get("data", {}), SPATIALDATA_DEFAULTS)
    return add_spatial_dataset(vc, dataset_name, dataset, options=options)


def prepare_datasets(
    vc: VitessceConfig,
    template: dict[str, Any],
    template_path: Path,
) -> dict[str, VitessceConfigDataset]:

    datasets = template["datasets"]
    vitessce_datasets: dict[str, VitessceConfigDataset] = {}
    for dataset_name, dataset in datasets.items():
        if dataset["type"] == "anndata_zarr":
            vit_dataset = prepare_anndata_dataset(vc, dataset_name, template)
            vitessce_datasets.update(vit_dataset)
        if dataset["type"] == "spatialdata_zarr":
            vit_dataset = prepare_spatial_dataset(vc, dataset_name, template, template_path)
            vitessce_datasets.update(vit_dataset)

    return vitessce_datasets
