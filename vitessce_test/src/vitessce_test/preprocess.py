import shutil
from scipy.sparse import csc_matrix, issparse
import numpy as np
import pandas as pd
import anndata as ad
from spatialdata_io import xenium
from pathlib import Path
from typing import Any

from vitessce_test.settings import DATA_DIR

def write_with_backup(
    output_path: Path,
    write_func: Any,
) -> None:
    if output_path.exists():
        backup_path = output_path.with_name(f"{output_path.stem}_backup.zarr")
        _ = output_path.rename(backup_path)

        # Recover backed up data if write fails
        try:
            write_func(output_path)
        except Exception as e:
            if output_path.exists():
                shutil.rmtree(output_path)
            _ = backup_path.rename(output_path)
            raise RuntimeError(f"Failed to write sparse matrix to {output_path}: {e}")
        else:
            shutil.rmtree(backup_path)
    else:
        write_func(output_path)

def make_sparse_matrix(
    adata: ad.AnnData
) -> None:
    if not (issparse(adata.X) and adata.X.format == "csc"):                           # pyright: ignore[reportUnknownMemberType]
        adata.X = csc_matrix(adata.X)                   # pyright: ignore[reportUnknownMemberType,reportUnknownArgumentType]


def make_valid_column_names(
    adata: ad.AnnData
) -> None:
    obs_names: list[str] = list(adata.obs.columns)

    new_names: list[str] = []
    for name in obs_names:
        if "/" in name:
            print(f"Warning: Invalid column name: {name}")
            new_names.append(name.replace("/", "_"))
        else:
            new_names.append(name)
    adata.obs.columns = new_names


def handle_nullable_string_index(
    adata: ad.AnnData
) -> None:
    # Handle nullable string indexes for compatibility with older pandas versions.
    adata.var.index = pd.Index(
        adata.var.index.astype(str).to_numpy(),                          # pyright: ignore[reportUnknownMemberType]
        dtype=object,
    )
    adata.obs.index = pd.Index(
        adata.obs.index.astype(str).to_numpy(),                          # pyright: ignore[reportUnknownMemberType]
        dtype=object,
    )
    ad.settings.allow_write_nullable_strings=False


def read_anndata(
    source_path: Path
) -> ad.AnnData:
    if source_path.suffix == ".zarr":
        adata = ad.read_zarr(source_path)                            # pyright: ignore[reportUnknownMemberType]
    elif source_path.suffix == ".h5ad":
        adata = ad.read_h5ad(source_path)
    else:
        raise ValueError(f"Unsupported file format: {source_path}")
    return adata


def clean_up_anndata(
    source_path: Path,
) -> ad.AnnData:
    adata = read_anndata(source_path)

    # Clean up Anndata if necessary
    make_valid_column_names(adata)
    make_sparse_matrix(adata)
    handle_nullable_string_index(adata)

    return adata


def prepare_subset(
    source_path: Path,
    output_path: Path,
    options: dict[str, str]
) -> None:
    """
    Prepare a subset of the AnnData object based on the condition column and name.
    """
    adata = clean_up_anndata(source_path)

    condition_col, condition_name = options.get("subset", (None, None))
    if condition_col is None:
        raise ValueError("Condition column is required with subset option")
    if "/" in condition_col:
        condition_col = condition_col.replace("/", "_")
    if condition_col not in adata.obs.columns:
        raise ValueError(f"Condition column not found: {condition_col}")

    mask = adata.obs[condition_col] == condition_name            # pyright: ignore[reportUnknownVariableType]
    if not mask.any():
        raise ValueError(f"No cells with condition {condition_col} == '{condition_name}'.\nPossible values: " + ", ".join(adata.obs[condition_col].unique()))
    subset_adata = adata[mask].copy()

    make_sparse_matrix(subset_adata)

    if output_path.exists() and options.get("overwrite", False):
        write_with_backup(output_path, subset_adata.write_zarr)
    else:
        subset_adata.write_zarr(
            store=output_path
        )


def check_paths(
    source_path: Path,
    output_path: str | None,
    options: dict[str, str | None]
) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"Input path not found: {source_path}")

    if output_path is None:
        subset = options.get("subset", None)
        if subset is not None:
            _, subset_name = subset
            final_output_path = Path(DATA_DIR, source_path.stem + f"_{subset_name.lower().replace(' ', '_')}.zarr")
        else:
            final_output_path = Path(DATA_DIR, source_path.stem + "_corrected.zarr")
    else:
        final_output_path = Path(DATA_DIR, output_path).with_suffix(".zarr")

    if final_output_path.exists() and not options.get("overwrite", False):
        raise FileExistsError(f"Output already exists: {final_output_path} (use --overwrite to replace it)")
    if final_output_path.resolve() == source_path.resolve():
        raise ValueError("Output path cannot be the same as the source path")

    return final_output_path


def prepare_anndata(
    source_path: Path,
    output_path: str | None,
    options: dict[str, Any]
) -> None:
    final_output_path = check_paths(source_path, output_path, options)

    subset = options.get("subset", None)
    if subset is not None:
        prepare_subset(source_path, final_output_path, options)
    else:
        adata = clean_up_anndata(source_path)
        write_with_backup(final_output_path, adata.write_zarr)


def prepare_xenium(
    source_path: Path,
    output_path: str | None,
    options: dict[str, Any]
) -> None:
    final_output_path = check_paths(source_path, output_path, options)

    sdata = xenium(source_path)
    adata = sdata.tables["table"]

    umap_path = options.get("umap_path", None)
    if umap_path is not None and Path(source_path, umap_path).exists():
        umap_data = pd.read_csv(source_path / umap_path, index_col=0)
        umap_data_full = pd.DataFrame(index=adata.obs["cell_id"])
        umap_data_full.loc[umap_data.index, ["UMAP-1", "UMAP-2"]] = umap_data.loc[umap_data.index, ["UMAP-1", "UMAP-2"]]
        adata.obsm["X_umap"] = umap_data_full.to_numpy(np.float32)

    clusters_path = options.get("clusters_path", None)
    if clusters_path is not None and Path(source_path, clusters_path).exists():
        clusters = pd.read_csv(source_path / clusters_path, index_col=0)
        clusters_full = pd.DataFrame(index=adata.obs["cell_id"])
        clusters_full.loc[clusters.index, "Cluster"] = clusters.loc[clusters.index, "Cluster"]
        adata.obs["clusters"] = clusters_full["Cluster"]

    handle_nullable_string_index(adata)

    # Write X as sparse matrix
    make_sparse_matrix(adata)
    sdata.tables["table"] = adata

    write_with_backup(final_output_path, sdata.write)
