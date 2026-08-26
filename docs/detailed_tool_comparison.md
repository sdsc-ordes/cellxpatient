# Tool comparison

## Summary

| Criterion      | Vitessce [↓](#vitessce)   | WebAtlas [↓](#webatlas)  | MDV [↓](#mdv) |  UCSC Cell Browser [↓](#ucsc-cell-browser) |
| -------------- | ----------------------- | ---------------------------------- | ----------------- | ------------------- |
| Type           | Visualisation framework | Pipeline + portal (Vitessce-based) | Interactive analysis & visualisation web application | Complete viewer   |            |                                              |
| Language       | TS/JS, React, Python, R | Python, Nextflow, React | Python | Python, JS | 
| scRNA          | Yes                     | Yes                                | Yes              | Yes | 
| Spatial        | Yes    | Yes | Yes | Yes  | 
| Multiomics     | Yes  | No  | Possible | Yes | 
| Sustainability | High    | Medium  | High | High  | 
| Dev. Effort | High | medium | medium | low |


| Criterion      | ShinyCellModular  [↓](#shinycellmodular)  | scRNAseqApp [↓](#scrnaseqapp) | Cirrocumulus [↓](#cirrocumulus) | 
| -------------- | ---------------------- | ---------- |  ------------- | 
| Type           | Shiny app (modular) | Shiny app   | Complete interactive viewer | 
| Language       | R | R | Python | 
| scRNA          | Yes | Yes  | Yes | 
| Spatial        | No (soon) | Yes  | Yes | 
| Multiomics     | Partial |   Yes | Partial | 
| Sustainability | medium  | medium | medium |
| Dev. Effort |  low | low | low | 

## [Vitessce](https://vitessce.io/)

#### General

- **Languages:** Typescript/javascript/react. Has python and R interfaces
- **Maintainer:** HIDIVE Lab (Harvard Medical School)
- **Input formats:** AnnData, Mu-Zarr, SpatialData, CSV, Json (tutorial and
  detail explanation to convert data)
- **License:** MIT

#### Sustainability

- **Maintenance/Funding:** declared funding when publishing paper (2024):
  National Institutes of Health, the National Science Foundation, the Harvard
  Stem Cell Institute and the Chan Zuckerberg Initiative. Is embedded in the
  Human BioMolecular Atlas Program (HuBMAP), favor long maintenance.

#### Data types

- scRNA
- spatial
- multi-omics

#### Performance

- good data scalability (Zarr chunked data + multiscale pyramid)
- good reactivity (as advertised and tested with >1mio cells). Also tested on
  [HuBMAP Data Portal](https://portal.hubmapconsortium.org/)

Vitessce's publication reports scatterplot visualization of millions of cells,
heatmaps with >10'000 of features and support for multi GB images.

#### Features

- highly customisable
- support for clinical metatdata support (documented example with cell linked to disease state)
- not an analysis tool but good analysis results display

#### Main strengths

- customizable
- part of HuBMAP consortium
- probable long longevity

#### Main limitations

- not a ready-to-use solution

#### Deployement test

- highly extensible but only on the dev side, once built => fix layout 
- polished presentation. Interactivity seems limited but might depend on the view preparation.
- data preparation: need to prepare a config view (json file). Not clear if ready-to-use dataloaders to prepare config views exist.
- good documentation but steep learning curve to learn how to build custom views.






## [WebAtlas](https://cellatlas.io/webatlas)

#### General

- **Languages:** Nextflow for data pipeline, React for Webapp, Vitessce for visualisation
- **Maintainer:** Haniffa lab
- **Input formats:** h5ad, tif, SpaceRanger, Xenium/Visium, MERSCOPE output, CSV, MERFISH
- **License:** MIT

#### Sustainability

- **Maintenance/Funding:** Developped and maintained by the Haniffa lab. Mostly Wellcome Sanger Institute mentioned in paper. Funding from several sources (Wellcome Trust, NIHR, Medical research council,...)

#### Data types

- scRNA
- spatial
- multi-omics not mentioned

#### Performance

- good data scalability and reactivity ([demo with million of cells, with spatial data](https://cellatlas.io/studies/webatlas/dataset/166/vitessce))
- [2025 Nature atlas](https://webatlas.cog.sanger.ac.uk/dev/index.html?theme=dark&config=https://f1-fb121.s3.us-east-1.amazonaws.com/Merfish_F1_FB121/0.5.2/F1_FB121-scRNAseq-config.json) containing more than 18 million spatially resolved cells used WebAtlas for its interactive MERFISH browser 


#### Features

- no documented statistical analysis
- clinical integration seems possible. Include custom metadata in Anndata obs

#### Main strengths

- Vitessce-based visualisation
- Already built web app to display with Vitessce

#### Main limitations

- App repo didn't have contributions since 3 years
- Not strong maintenance




## [MDV](https://mdv.ndm.ox.ac.uk/)

#### General

- **Languages:** Python (available Docker container)
- **Maintainer:** NDM (Nuffield department of Medicine) Data Platform, University of Oxford
- **Input formats:** h5ad, MuData, zarr, vcf. csv. Mentions custom data loaders to support wide range of data source
- **License:** GPL-3

#### Sustainability

- **Maintenance/Funding:** Institutionally embedded. No explicit grant/funding mentioned.

#### Data types

- scRNA
- spatial
- multi-omics
- multi-modal with links between data tables

#### Performance

- excellent reactivity from demo project
- scalable to large data (Nature paper mentions 10mio data items). Lazy loading, min 4GB RAM for web

#### Features

- designed to support multi-modality
- many plots/functionalities
- clinical metadata supported


#### Main strengths

- multi-modality
- clinical metadata support 
- already containerised


#### Main limitations

- sparse documentation


#### Local deployement
- docker containers already available (one for PostgreSQL database, one for MDV app, user authentification possible)
- data preparation: dataloaders provided for common transcriptomics data. Smooth for spatial (Xenium, Visium) data, buggy with anndata/pandas version for h5ad.
- layout organised into "View". Each view is a window that can contain several plots/windows. 
- plots lack polishness (axis legend not visible if too long, stacked on each other if too many, not manually customisable/editable)
- nicely interactivity (list of plots to build on the spot, can manually define and change the settings of the plots)




## [UCSC Cell browser](https://cells.ucsc.edu/?)

#### General

- **Languages:** Python, Javascript
- **Maintainer:** UCSC Genome browser organisation (Genomics Institute, UC Santa Cruz)
- **Input formats:** Seurat RDS/RData/Robj, Scanpy h5ad, Loom, TSV/CSV
- **License:** GPL3.0

#### Sustainability

- **Maintenance/Funding:** since 2023, funding from NIMH BRAIN and CIRM DISC0 grant

#### Data types

- scRNA
- spatial
- multi-omics

#### Performance

- fast lightweight browser (uses static, precomputer layout)
- demo demonstrates excellent speed and reactivity


#### Features

- no native statistical analyses 
- display statistical plots and DE tables if externally generated
- clinical metadata support could be possible. UCSC metadata is flexible and can be used to filter, color cells.

#### Main strengths

- strong ecosystem behind UCSC
- good reactivity and easy to use browser
- local deployement supported

#### Main limitations

- long term maintenance
- limited extension

#### Deployement test
- pip package
- command to prepare h5ad (from Scanpy) to view in UCSC. Smooth conversion. No extra step needed.
- no comprehensive data loaders for all common scRNA and **spatial transcriptomics** (especially) data -> need additional data preparation layer!!!
- web browser built once (folder with hmtl/css/js files, usable on any static web server)
- each new dataset gets added to the html local folder -> might need additional steps to handle the sensitive data and authentification handling
- no interactive annotation, only reading the datasets
- efficient and simple viewer if all required features are covered



## [ShinyCellModular](https://monashbioinformaticsplatform.github.io/ShinyCellModular/)

#### General

- **Languages:** R, Shiny, Docker support
- **Maintainer:** Monash Genomics and Bioinformatics Platform
- **Input formats:** Seurat object/RDS
- **License:** GPL3.0

#### Sustainability

- **Maintenance/Funding:** Not found explicitly. Likely via funding of the Monash Genomics and Bioinformatics Platform.

#### Data types

- scRNA
- multimodal datasets

#### Performance

- HDF5 and Parquet for on-demand loading
- scalable to large data unclear
- demo suffers from some latency

#### Features

- interactive DE analysis
- violin/box plots, heatmaps 
- clinical metadata supported


#### Main strengths

- modularity
- statistical analysis support

#### Main limitations

- recent project, maturity?
- no spatial support




## [scRNAseqApp](https://github.com/jianhong/scRNAseqApp)

#### General

- **Languages:** R, Shiny
- **Maintainer:** Jianhong Ou (bioinformatician at Morgridge Institute for Research)
- **Input formats:** Seurat Object
- **License:** GPL-3

#### Sustainability

- **Maintenance/Funding:** not mentioned

#### Data types

- scRNA
- spatial
- multi-omics

#### Performance

- scaling: package intended for exploration not heavy computation clearly stated. h5-based expression matrix, only selected genes loaded 
- probable medium reactivity (shiny application)


#### Features

- clustering and filtering using metadata, clinical metadata supported
- no DE analysis
- interactive cell annotation
- common plots: heatmap/violin/dot plots...

#### Main strengths

- multi-modal (spatial, scRNA, omics)


#### Main limitations

- long-term maintenance and development hard to assess
- no accessible demo
- limited docs





## [Cirrocumulus](https://cirrocumulus.readthedocs.io/en/latest/documentation.html)

#### General

- **Languages:** Python
- **Maintainer:** Klarmann Cell Observatory, Broad Institute. Also The General Hospital Corporation mentioned
- **Input formats:** h5ad, 10x h5, Xenium, MERFISH, loom, Seurat, TileDB, or zarr 
- **License:** BSD-3

#### Sustainability

- **Maintenance/Funding:** Recent project but institutionally embedded. No explicit grant/funding mentioned.

#### Data types

- scRNA
- spatial

#### Performance

- use custom Cirrocumulus format (either zarr, jsonl or parquet) for efficient partial dataset retrieval (can be used over network)
- scalable to large data

#### Features

- DE analysis
- violin/box plots, heatmaps 
- clinical metadata supported (via arbitrary anndata.obs metadata)
- multi-user server deployement

#### Main strengths

- scRNA + spatial
- easy deployement

#### Main limitations

- project maturity and sustainability
- sparse documentation
