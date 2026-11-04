import shutil
from pathlib import Path
from typing import Any

import anndata as ad
import dask
import dask.array as da
import numpy as np
import pandas as pd
import zarr
from scipy.sparse import (
    csc_matrix,
    issparse,
)
from spatialdata.models import Image2DModel
from spatialdata.transformations.transformations import Identity
from spatialdata_io import xenium
from spatialdata_io._constants._constants import XeniumKeys
from tifffile import TiffFile, imread

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
        except Exception:
            if output_path.exists():
                shutil.rmtree(output_path)
            _ = backup_path.rename(output_path)
            raise
        else:
            shutil.rmtree(backup_path)
    else:
        write_func(output_path)


def check_paths(
    source_path: Path, output_path: str | None, options: dict[str, str | None]
) -> Path:
    if not source_path.exists():
        raise FileNotFoundError(f"Input path not found: {source_path}")

    if output_path is None:
        subset = options.get("subset", None)
        if subset is not None:
            _, subset_name = subset
            final_output_path = Path(
                DATA_DIR,
                source_path.stem + f"_{subset_name.lower().replace(' ', '_')}.zarr",
            )
        else:
            final_output_path = Path(DATA_DIR, source_path.stem + "_corrected.zarr")
    else:
        final_output_path = Path(DATA_DIR, output_path).with_suffix(".zarr")

    if final_output_path.exists() and not options.get("overwrite", False):
        raise FileExistsError(
            f"Output already exists: {final_output_path} (use --overwrite to replace it)"
        )
    if final_output_path.resolve() == source_path.resolve():
        raise ValueError("Output path cannot be the same as the source path")

    return final_output_path


def make_sparse_matrix(adata: ad.AnnData) -> None:
    if not (issparse(adata.X) and adata.X.format == "csc"):  # pyright: ignore[reportAttributeAccessIssue]
        adata.X = csc_matrix(adata.X)


def make_valid_column_names(adata: ad.AnnData) -> None:
    obs_names: list[str] = list(adata.obs.columns)

    new_names: list[str] = []
    for name in obs_names:
        if "/" in name:
            print(f"Warning: Invalid column name: {name}")
            new_names.append(name.replace("/", "_"))
        else:
            new_names.append(name)
    adata.obs.columns = new_names


def handle_nullable_string_index(adata: ad.AnnData) -> None:
    # Handle nullable string indexes for compatibility with older pandas versions.
    adata.var.index = pd.Index(
        adata.var.index.astype(str).to_numpy(),
        dtype=object,
    )
    adata.obs.index = pd.Index(
        adata.obs.index.astype(str).to_numpy(),
        dtype=object,
    )
    ad.settings.allow_write_nullable_strings = False


def read_anndata(source_path: Path) -> ad.AnnData:
    if source_path.suffix == ".zarr":
        adata = ad.read_zarr(source_path)
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
    source_path: Path, output_path: Path, options: dict[str, str]
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

    mask = adata.obs[condition_col] == condition_name
    if not mask.any():
        raise ValueError(
            f"No cells with condition {condition_col} == '{condition_name}'.\nPossible values: "
            + ", ".join(adata.obs[condition_col].unique())
        )
    subset_adata = adata[mask].copy()

    make_sparse_matrix(subset_adata)  # pyright: ignore[reportArgumentType]

    if output_path.exists() and options.get("overwrite", False):
        write_with_backup(output_path, subset_adata.write_zarr)  # pyright: ignore[reportAttributeAccessIssue]
    else:
        subset_adata.write_zarr(  # pyright: ignore[reportAttributeAccessIssue]
            store=output_path
        )


def prepare_anndata(
    source_path: Path, output_path: str | None, options: dict[str, Any]
) -> None:
    final_output_path = check_paths(source_path, output_path, options)

    subset = options.get("subset", None)
    if subset is not None:
        prepare_subset(source_path, final_output_path, options)
    else:
        adata = clean_up_anndata(source_path)
        write_with_backup(final_output_path, adata.write_zarr)


def get_morpho_channels(source_path) -> tuple[list[Path], list[str]]:
    morphology_focus_dir = source_path / XeniumKeys.MORPHOLOGY_FOCUS_DIR
    files = [
        f for f in morphology_focus_dir.glob("*.ome.tif") if not f.name.startswith("._")
    ]
    filenames = {file.name for file in files}
    if XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_IMAGE.value.format(0) in filenames:
        if len(filenames) not in [1, 4]:
            raise ValueError(
                "Expected 1 (no segmentation kit) or 4 (segmentation kit) files in the morphology focus directory, "
                f"found {len(files)}: {files}"
            )
        if filenames != {
            XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_IMAGE.value.format(i)
            for i in range(len(files))
        }:
            raise ValueError(
                "Expected files in the morphology focus directory to be named as "
                f"{XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_IMAGE.value.format(0)} to "
                f"{XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_IMAGE.value.format(len(filenames) - 1)}, found {filenames}"
            )
        if len(filenames) == 1:
            channel_names = {
                0: XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_0.value,
            }
        else:
            channel_names = {
                0: XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_0.value,
                1: XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_1.value,
                2: XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_2.value,
                3: XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_3.value,
            }
    else:
        raise ValueError(
            f"Unexpected file name format for the morphology focus image. "
            f"Expected: {XeniumKeys.MORPHOLOGY_FOCUS_CHANNEL_IMAGE.value.format(0)} "
            f"Got: {filenames}"
        )
    return files, list(channel_names.values())


def lazily_load_morpho_focus(
    source_path: Path,
):
    # Reuse channel names of spatialdata-io.xenium
    channel_paths, channel_names = get_morpho_channels(source_path)

    image_models_kwargs = {}
    image_models_kwargs["c_coords"] = channel_names

    # Align chunksize to that of the OME TIFF images
    with TiffFile(channel_paths[0]) as tif:
        tif_image = tif.pages[0]
        if tif_image.is_tiled:
            chunksize = (1, tif_image.tilelength, tif_image.tilewidth)
        else:
            chunksize = (1, 1024, 1024)
    image_models_kwargs["chunks"] = chunksize
    image_models_kwargs["scale_factors"] = [2, 2, 2, 2]

    # Lazily load all channels of the morphology focus Ome-Tiff(s)
    dask_channels = []
    for channel_path in channel_paths:
        root = zarr.open(imread(channel_path, return_as="zarr"))
        dask_channels.append(da.from_zarr(root["0"]))

    dask_image = da.stack(dask_channels, axis=0)
    if dask_image.ndim == 2:
        dask_image = da.expand_dims(dask_image, axis=0)

    return Image2DModel.parse(
        dask_image,
        transformations={"global": Identity()},
        dims=("c", "y", "x"),
        rgb=None,
        **image_models_kwargs,
    )


def prepare_xenium(
    source_path: Path, output_path: str | None, options: dict[str, Any]
) -> None:

    if options.get("single_threaded", False):
        dask.config.set(scheduler="synchronous")

    final_output_path = check_paths(source_path, output_path, options)

    # Manually load morphology image to bypass full Ome-Tif in memory
    sdata = xenium(
        source_path,
        transcripts=False,
        nucleus_labels=False,
        cells_labels=False,
        morphology_mip=False,
        morphology_focus=False,
    )

    # Add UMAP embeddings and cell clusters from Xenium output
    adata = sdata.tables["table"]

    umap_path = options.get("umap_path", None)
    if umap_path is not None and Path(source_path, umap_path).exists():
        umap_data = pd.read_csv(source_path / umap_path, index_col=0)
        umap_data_full = pd.DataFrame(index=adata.obs["cell_id"])
        umap_data_full.loc[umap_data.index, ["UMAP-1", "UMAP-2"]] = umap_data.loc[
            umap_data.index, ["UMAP-1", "UMAP-2"]
        ]
        adata.obsm["X_umap"] = umap_data_full.to_numpy(np.float32)

    clusters_path = options.get("clusters_path", None)
    if clusters_path is not None and Path(source_path, clusters_path).exists():
        clusters = pd.read_csv(source_path / clusters_path, index_col=0)
        clusters_full = pd.DataFrame(index=adata.obs["cell_id"])
        clusters_full.loc[clusters.index, "Cluster"] = clusters.loc[
            clusters.index, "Cluster"
        ]
        adata.obs["clusters"] = clusters_full["Cluster"]

    handle_nullable_string_index(adata)

    # Write X as sparse matrix
    make_sparse_matrix(adata)
    sdata.tables["table"] = adata

    # Manually load the OME TIFF in a chunkwise manner
    sdata.images["morphology_focus"] = lazily_load_morpho_focus(source_path)

    # Write using SpatialData write function
    write_with_backup(final_output_path, sdata.write)
