# Candidate repositories
 
Initial list of open-source projects/tools that could replace CellXGene for interactive exploration and visualisation of single-cell RNA-seq data.

## List of matching tools

Inclusion in the list does not imply recommendation. Notes are here to guide the ranking for more detailed evaluation.
 
| Project | Language  | Data type |  Initial notes   | Priority  |
| ------- | --------- | --------- | ---------------- | --------- |
| [Vitessce](https://vitessce.io/)   |   Web app (also Python and R widgets)   | spatial, scRNA, multi-omics | Browser-based single-cell and spatial visualization; good documentation, good versatility. More manual implementation and customization, only visualisation engine | top |
| [WebAtlas](https://www.nature.com/articles/s41592-024-02371-x) | Python | Single cell and spatial transcriptomics | Web app (React), uses Vitessce as visualisation framework. Analysis pipeline with nextflow. Not sure about maintenance longevity | medium/top |
| [UCSC Cell Browser](https://genome.ucsc.edu/singlecell.html)  |    Python for data processing + java libraries for visualisation    | only single-cell data, spatial transcriptomics support (Visium)  | Good reactivity, gene expression analysis, heatmap, violin plots.    | top
|[ShinyCellModular]()| R | scRNA, multiomics, spatial seems planned for the future | Interactive viewer and modular approach that allow app customisation with several analysis modules. Seems to have maintenance | top
| [scRNAsrqApp](https://github.com/jianhong/scRNAseqApp)| R | scRNA, spatial and multi-omics | R Shiny App, interactive exploration and visualisaiton of scRNA and spatial data and multi-omics, web based interface with diverse plots and functionalities (violin plots, heatmaps, filtering). Seems recently maintained | top
| [Cirrocumulus](https://cirrocumulus.readthedocs.io/en/latest/index.html) | Python | scRNA and spatial | Easily deployable, interactive visualisaiton and annotation, violin/heatmap plots, differential expression analysis | top |
| [scSpatialExplorer](https://github.com/FredPont/spatial) | Go | mostly spatial transcriptomcis,  | User friendly interface (advertised), great graphics, analysis options: clustering, gene expression, pathways, great interactivity. Desktop app! Not web based  | medium |
| [scSignatureExplorer](https://github.com/FredPont/signature) | Go | mostly scRNA  | User friendly interface (advertised), great graphics, analysis options: clustering, gene expression, great interactivity. Desktop app! Not web based | medium
| [Kana](https://kanaverse.org) | Javascript (web app), R (preprocessing), C++ (webassembly) | only single cell data | good reactivity, more or less recently maintained  | medium |
| [Crescent](https://crescent.cloud/) | R, python, react | scRNA only | easy to use web portal, R package and also containerized version, analysis and visualisation pipeline. Maybe heavier | medium
| [scOrange](https://singlecell.biolab.si/#Orange-Features) | Python | scRNA only | Orange3 add-on for single-cell analysis, with widgets for gene filtering, marker analysis,... and interactive visualization; still maintained, part of a broader ecosystem, only scRNA so far. Not sure if easy to deploy. | medium
| [iSEE](http://shiny.imbei.uni-mainz.de:3838/iSEE)| R | scRNA only | Demo not loading, sparse documentation. Interactive analysis and visualisation. Seems recently maintained. | low/medium
| [OmniCellX](https://github.com/longrw/OmniCellX#browser-mode) | R | scRNA | Includes QC/filtering, dimensionality reduction, clustering, cluster annotation, differential expression, and browser views such as UMAP, feature plots, violin plots and dot plots. | medium
| [iS-CellR](https://github.com/immcore/iS-CellR)| R | scRNA only |  Good functionality and visualisation, differential expression, clustering. Seems outdated | low
| [Cerebro](https://github.com/romanhaa/Cerebro) | R | only scRNA | Deployable, meant for non-tech users, interactive visulaisations (gene pathways, gene expression...). Active maintenance? Seems outdated | low
| [Cellar](https://github.com/euxhenh/cellar) | Python | scRNA and spatial, other omics | Supports preprocessing, dimensionality reduction, clustering, DE gene testing, enrichment analysis, cluster and gene visualization modules, projection to spatial tiles, label transfer, and semi-supervised clustering among others. No recent contributions... | low
