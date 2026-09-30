from pathlib import Path
from typing import Any, cast
import json
import pandas as pd
import anndata as ad
import zarr

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


SAMPLE_ID_DEFAULT = "sample"


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


def read_anndata_obs(zarr_path: Path) -> pd.DataFrame:
    adata = ad.read_zarr(zarr_path)
    return cast(pd.DataFrame, adata.obs)


def build_data_url(path: Path) -> str:
    return (
        f"{DATA_URL}/"
        f"{path.relative_to(DATA_DIR).as_posix()}"
    )


def generate_all_sample_pairs(
    sample_grouping_cols: list[str],
    adata_obs: pd.DataFrame
) -> list[Any]:

    pairs = []

    for col in sample_grouping_cols:
        if col not in adata_obs.columns:
            raise ValueError(
                f"Sample grouping column {col} does not exist in obs."
            )
        #series = cast(pd.Series, adata_obs[col])
        values = [str(val) for val in adata_obs[col].unique()]
        n_values = len(values)
        for first in range(n_values):
            for second in range(first+1, n_values):
                pairs.append(
                    [
                        col,
                        [values[first], values[second]]
                    ])

    return pairs


def write_sample_sets(
    adata_obs: pd.DataFrame,
    sample_id: str,
    sample_categories: set[str],
    comparison_zarr_path: Path
):
    columns_subset = [*sample_categories, sample_id]
    samples_metadata = pd.DataFrame(adata_obs[columns_subset].copy())
    samples_metadata = samples_metadata.drop_duplicates(
        subset=sample_id).set_index(sample_id)
    samples_adata = ad.AnnData(obs=samples_metadata)
    samples_adata.write_zarr(comparison_zarr_path)


def prepare_sample_pairs(
    adata_obs: pd.DataFrame,
    comparison_data: dict[str,Any]
) -> tuple[list[Any], set[str]]:
    sample_group_pairs: list[Any] = []
    sample_categories: set[str] = set()

    sample_grouping_cols = comparison_data.get("sample_grouping_cols", [])
    if sample_grouping_cols:
        sample_categories |= set(sample_grouping_cols)
        sample_group_pairs += generate_all_sample_pairs(sample_grouping_cols, adata_obs)

    sample_pairs = comparison_data.get("sample_pairs", [])
    if sample_pairs:
        sample_group_pairs += sample_pairs
        sample_categories |= {sample_pair[0] for sample_pair in sample_pairs}

    return sample_group_pairs, sample_categories


def write_comparison_metadata(
    zarr_path: Path,
    metadata: dict[str, Any]
) -> None:
    metadata_json = json.dumps(metadata)
    metadata_bytes = metadata_json.encode("utf-8")

    root = zarr.open_group(
        zarr_path,
        mode="a"
    )
    uns = root.require_group("uns")
    arr = uns.create_array(
        "comparison_metadata",
        shape=(),
        chunks=(),
        dtype=f"|S{len(metadata_bytes)}",
        filters=None,
        compressors=None,
    )
    arr[...] = metadata_bytes
    arr.attrs.update({
        "encoding-type": "string",
        "encoding-version": "0.2.0",
    })


def build_comparison_metadata(
    sample_col: str,
    obs_type_paths: list[str],
    sample_comparison_pairs: list[Any]
) -> dict[str,Any]:

    # Only col name is needed, not the full path from zarr root
    obs_type_cols = [Path(obs_type_path).stem for obs_type_path in obs_type_paths]
    metadata_dict = {                                  # pyright: ignore[reportUnknownVariableType]
        "schema_version": "0.0.2",
        "cell_type_cols": obs_type_cols,
        "sample_id_col": sample_col,
        "sample_group_pairs": sample_comparison_pairs,
        "comparisons": {}
    }
    return metadata_dict


def prepare_comparison_metadata(
    adata_path: Path,
    comparison_config: dict[str, Any],
    obs_type_paths: list[str]
)-> list[dict[str,Any]]:

    dataset_path = Path(str(adata_path).split(".zarr")[0])
    comparison_zarr_path = dataset_path.parent / (dataset_path.stem + "_comparison.zarr")

    adata_obs = pd.DataFrame(ad.read_zarr(adata_path).obs)
    sample_col = comparison_config.get("sample_id_col", SAMPLE_ID_DEFAULT)
    sample_comparison_pairs, comparison_categories = prepare_sample_pairs(
        adata_obs, comparison_config
    )
    write_sample_sets(adata_obs, sample_col, comparison_categories, comparison_zarr_path)

    comparison_metadata = build_comparison_metadata(
        sample_col, obs_type_paths, sample_comparison_pairs)
    write_comparison_metadata(
        comparison_zarr_path, comparison_metadata)

    url = build_data_url(comparison_zarr_path)
    comparison_files_config = [
        {
            "file_type": "comparisonMetadata.anndata.zarr",
            "url": url,
            "coordination_values": {
                "obsType": "cell",
                "sampleType": "sample"
            },
            "options": {
                "path": "uns/comparison_metadata"
            }
        },
        {
            "file_type": "sampleSets.anndata.zarr",
            "url": url + "/obs",
            "coordination_values": {
                "sampleType": "sample"
            },
            "options": {
                "sampleSets": [{"name": comparison_cat, "path": comparison_cat}
                for comparison_cat in comparison_categories]
            }
        }
    ]
    url = build_data_url(adata_path)
    comparison_files_config.append({
            "file_type": "sampleEdges.anndata.zarr",
            "url": url,
            "coordination_values": {
                "obsType": "cell",
                "sampleType": "sample"
            },
            "options": {
                "path": f"obs/{sample_col}"
            }
        }
    )
    return comparison_files_config


def add_anndata_dataset(
    vc: VitessceConfig,
    dataset_name: str,
    dataset: dict[str, Any],
) -> dict[str, VitessceConfigDataset]:

    options = get_dataset_data(dataset.get("data", {}), ANNDATA_DEFAULTS)
    adata_path = get_valid_dataset_path(dataset)

    # Add datasets to the widget (dataset = container for file per data type)
    vit_dataset = vc.add_dataset(
        name=dataset_name)

    # Use AnnDataWrapper to automatically handle pahts to relevant data
    _ = vit_dataset.add_object(
        AnnDataWrapper(
            adata_path=adata_path.relative_to(DATA_DIR),
            **options
        )
    )

    comparison_metadata = dataset.get("sample_comparison", {})
    if comparison_metadata:
        comparison_files = prepare_comparison_metadata(
            adata_path, comparison_metadata, options.get("obs_set_paths", []))
        for file_info in comparison_files:
            _ = vit_dataset.add_file(                      # pyright: ignore[reportUnknownMemberType]
                file_type=file_info["file_type"],
                url=file_info["url"],
                options=file_info["options"],
                coordination_values=file_info["coordination_values"]
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

    comparison_metadata = dataset.get("sample_comparison", {})
    if comparison_metadata:
        comparison_files = prepare_comparison_metadata(
            spatialzarr_path, comparison_metadata, options.get("obs_set_paths", []))
        for file_info in comparison_files:
            _ = vitessce_dataset.add_file(
                file_type=file_info["file_type"],
                url=file_info["url"],
                options=file_info["options"],
                coordination_values=file_info["coordination_values"]
            )

    return { dataset_name: vitessce_dataset }


def prepare_datasets(
    vc: VitessceConfig,
    datasets: dict[str, Any]
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
