## Sample-level comparison

Some Vitessce views can compare two groups of samples side by side (for example
one violin per group). They use sample-level coordination types:

- `sampleType`: links the views to the sample data;
- `sampleSetSelection`: the two compared groups, as `[control, case]`;
- `sampleSetFilter`: restricts the views to the selected groups.

Mapping cells to groups requires additional files in the view config (see the
[file type documentation](https://vitessce.io/docs/data-file-types/)):

- `sampleSets.csv`: one row per sample, one column per category (e.g. disease).
  Needed by the built-in `sampleSetPairManager` view and the Group Builder.
- `sampleEdges.anndata.zarr`: the AnnData obs column mapping each cell to its
  sample.
- `comparisonMetadata.anndata.zarr`: metadata describing the comparison (only
  for the built-in `sampleSetPairManager` view).

`build.py` generates these files when a dataset in the template has a
`sample_comparison` block (see
[example_template.yaml](../../data/processed/example_template.yaml)).

### Group Builder

The Group Builder is a custom view (a Vitessce plugin in `frontend/`) for
defining the two groups interactively, from the sample metadata in
`sampleSets.csv`. Within a category, selected values are combined with OR;
across categories, with AND.

On **Apply comparison**, the server adds a generated category, "Custom
comparison", to the sample sets, with the values "Group A", "Group B" and
"Other". The Group Builder then sets `sampleSetSelection` and `sampleSetFilter`
to the two groups, which switches the coordinated views to comparison mode.
**Reset** removes the comparison.

For this to work, the Group Builder and the comparison views must share the same
coordination scopes for `dataset`, `sampleType`, `sampleSetSelection`,
`sampleSetFilter` and `sampleSetColor`.

### Notes on Vitessce views

The main Vitessce documentation listing the available views is not exhaustive.
The source code and other parts of the documentation reveal more views, in
particular for comparing pairs of sample groups (e.g. case vs control):

- **sampleSetPairManager**: selects predefined pairs of sample groups to
  compare, and coordinates the views at sample level. The pairs must follow the
  format described [here](https://vitessce.io/docs/data-comparative/), and the
  three files listed above must be provided.
- **gating**: a scatterplot of gene-wise embeddings, with the expression of a
  selected gene A on X and of a gene B on Y.
- **dotplot**: works with the sample set coordination types to show dot plots
  per selected gene, comparing the selected pair of groups.
- **featureStatsTable**, **volcanoPlot**, **obsSetCompositionBarPlot**,
  **treemap**: require precomputed differential expression results.
