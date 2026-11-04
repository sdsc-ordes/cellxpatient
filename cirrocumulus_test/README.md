# Cirrocumulus Test Environment

This directory contains the setup used to test [Cirrocumulus](https://github.com/lilab-bcb/cirrocumulus) for viewing scRNA and spatial transcriptomics data.


## Installation

No deployment is needed for local testing: Cirrocumulus is installed as a Python package and serves the viewer itself.

```bash
just nix develop cirrocumulus
```

> **Note:** `fsspec` is pinned to the 2023.1.0. Cirrocumulus does not pin it, and newer fsspec releases reject the glob pattern Cirrocumulus uses when opening a dataset (`ValueError: Invalid pattern: '**' can only be an entire path component`).


## Usage

Datasets are opened directly, without conversion, using `cirro launch`. The viewer opens in the browser at the URL printed in the terminal.

The current setup has been tested with both a spatial and an scRNA dataset:

- the **Xenium 0OE1 example** dataset provided by Antonin Thiebault
- the **scRNA-seq `.h5ad`** dataset of the Dunlap et al. 2022 paper (available on the [Skin Science Foundation BioHub](https://biohub.skinsciencefoundation.org/download/Dunlap_2022_all_final_label_transfer_swapped.h5ad))

### scRNA-seq / h5ad

```bash
cirro launch ../data/raw/<path_to_h5ad>
```

### Xenium

Cirrocumulus does not read the Xenium output folder itself. Give it the gene expression matrix file `.h5` from the Xenium output folder:

```bash
cirro launch ../data/raw/<path_to_xenium_folder>/cell_feature_matrix.h5
```
