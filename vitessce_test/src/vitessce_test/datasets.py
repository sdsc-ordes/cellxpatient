from pathlib import Path
from typing import Any

from vitessce import (
    AnnDataWrapper,
    SpatialDataWrapper,
    VitessceConfig,
)
from vitessce.config import (
    VitessceConfigDataset,
)

from vitessce_test.settings import DATA_DIR, DATA_URL


ANNDATA_DEFAULTS = {
    "obs_embedding_paths": ["obsm/X_umap"],
    "obs_embedding_names": ["UMAP"],
    "obs_set_paths": ["obs/pred_cell_type"],
    "obs_set_names": ["Cell Type"],
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


def get_valid_dataset_path(
    options: dict[str, Any],
) -> Path:
    dataset_path = options.get("dataset_path", None)
    if dataset_path is None:
        raise ValueError("dataset_path is required in YAML template per dataset entry.")
    dataset_path = Path(DATA_DIR, dataset_path)
    if not dataset_path.exists():
        raise ValueError(f"Dataset path {dataset_path} does not exist")
    return dataset_path


def get_dataset_data(
    dataset_data: dict[str, Any],
    defaults: dict[str, Any]
) -> dict[str, Any]:
    return {**defaults, **dataset_data}


def add_anndata_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    dataset: dict[str, Any],
) -> dict[str, VitessceConfigDataset]:

    options = get_dataset_data(dataset.get("data", {}), ANNDATA_DEFAULTS)
    adata_path = get_valid_dataset_path(dataset)

    # Add datasets to the widget (dataset = container for file per data type)
    vit_dataset = vc.add_dataset(                       # pyright: ignore[reportUnknownMemberType]
        name=dataset_name)

    # Use AnnDataWrapper to automatically handle pahts to relevant data
    _ = vit_dataset.add_object(                         # pyright: ignore[reportUnknownMemberType]
        AnnDataWrapper(
            adata_path=adata_path.relative_to(DATA_DIR),
            **options
        )
    )
    return {dataset_name: vit_dataset}


def add_spatial_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    dataset: dict[str, Any],
) -> dict[str, VitessceConfigDataset]:

    options = get_dataset_data(dataset.get("data", {}), SPATIALDATA_DEFAULTS)
    spatialzarr_path = get_valid_dataset_path(dataset)
    obs_seg_paths = options.pop("obs_seg_paths")

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
        url = f"{DATA_URL}/{spatialzarr_path.relative_to(DATA_DIR).as_posix()}"
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


def prepare_datasets(
    vc: VitessceConfig,
    datasets: dict[str, Any],
) -> dict[str, VitessceConfigDataset]:

    vitessce_datasets: dict[str, VitessceConfigDataset] = {}
    for dataset_name, dataset in datasets.items():
        if dataset["type"] == "anndata_zarr":
            vit_dataset = add_anndata_dataset(vc, dataset_name, dataset)
            vitessce_datasets.update(vit_dataset)
        if dataset["type"] == "spatialdata_zarr":
            vit_dataset = add_spatial_dataset(vc, dataset_name, dataset)
            vitessce_datasets.update(vit_dataset)

    return vitessce_datasets
