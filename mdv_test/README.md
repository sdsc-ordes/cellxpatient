# MDV Test Environment

This directory contains the setup used to test [MDV](https://github.com/Taylor-CCB-Group/MDV) and prepare scRNA and spatial transcriptomics data so that it can be viewed using MDV. 


## Installation

MDV runs locally using Docker. The local deployment follows the installation procedure referenced in the [MDV documentation](https://mdv.ndm.ox.ac.uk/docs/installation/installation-manual#option-2-docker-full-installation) and uses their shell script `deploy.sh`. 

```bash
chmod +x deploy.sh
./deploy.sh
```

The script checks that Docker is installed and running, prepares the environment configuration, pulls the required Docker images, and starts the services using Docker Compose.

Once running, MDV is available at:

```text
http://localhost:5055
```

> **Note:** Running `deploy.sh` creates a local `.env` file before starting the MDV and PostgreSQL containers. The values in this file are therefore used during deployment. The provided `.env_example` documents the configuration used for this test environment and can be used as a reference when answering the setup prompts. Database credentials should not be changed after the database volume has been initialized unless the database configuration is updated accordingly.


## Data preparation

Before scRNA-seq or spatial transcriptomics data can be opened in MDV, it must first be converted into an MDV project using the mdvtools package.

When working from the `mdv_test` directory, mdvtools should already be available in the development shell. Otherwise, start the MDV development environment with:

```bash
just nix develop mdv
```

The current setup has been tested with both a spatial and scRNA dataset:

- the **Xenium 0OE1 example** dataset provided by Antonin Thiebault
- the **scRNA-seq `.h5ad`** dataset of the 

In both cases, `mdvtools` is used to convert the input data into an MDV project directory. This directory is then archived as a .zip file, which can be imported directly into the MDV web application.

### Xenium

The Xenium example was converted into an MDV project using the convert-spatial subcommand. This subcommand expects a SpatialData object saved in Zarr format. Here are the steps to prepare the zip folder.

In python interpreter:
```python
from spatialdata_io import xenium
sdata = xenium(path="./path_to_xenium_folder")
sdata.write("zarr_output.zarr")
```

In terminal:
```bash
mdvtools convert-spatial <output_folder> <path_to_xenium_zarr>
zip -r <archive_name>.zip <output_folder> 
```

### scRNA-seq / h5ad

> Note: The latest mdvtools version pins a recent anndata release (0.12.2), but compatibility issues occur when converting .h5ad files that have probably been created with newer anndata/pandas versions.
In particular, newer pandas string dtypes yield an error during conversion.
For reproducibility, the helper script prepare_h5ad_for_mdv.py can be used to clean an input .h5ad file before running mdvtools. It converts string indices and string metadata columns to plain object.

The scRNA dataset was converted into an MDV project using the convert-scanpy subcommand. Here are the steps to prepare the zip folder.


```bash
# If necessary, prepare the h5ad
python prepare_h5ad_for_mdv.py <path_to_h5ad>

mdvtools convert-scanpy <output_folder> <path_to_h5ad>
zip -r <archive_name>.zip <output_folder> 
```
