## View templates

Vitessce configurations are generated programmatically with the Vitessce Python
API in [build.py](../../src/cellxpatient/build.py). To make views easier to
write, a view is described in a more readable YAML template (see
[example_template.yaml](../../data/processed/example_template.yaml)), which
`clxpt build` turns into a Vitessce JSON config.

### Template structure

Besides a `name` and a `description`, the YAML template has three main sections,
plus an optional `custom` block.

#### Datasets

Defines the datasets used in the view and, when required, paths to specific
elements within them. Each key is a dataset ID, which the views and coordination
sections refer to. A dataset has:

- a `type`: `anndata_zarr` or `spatialdata_zarr`;
- a `dataset_path`, relative to `data/processed/`;
- optionally, `data`: paths to elements within the store. Default paths are used
  for standard AnnData and SpatialData structures, so the template only needs to
  specify paths that differ from these defaults. The defaults are in
  [datasets.py](../../src/cellxpatient/datasets.py);
- optionally, `grid_offset_xy`, which shifts all the views of the dataset on the
  grid;
- optionally, `sample_comparison`, which prepares the files needed to compare
  groups of samples (see [sample_comparison.md](sample_comparison.md)).

#### Views

Defines which Vitessce views are displayed, which datasets they refer to, and
their position and size on a grid of 12 columns.
`grid_xywh: [x, y, width, height]` counts in grid cells from the top left. There
are as many rows as the layout uses, and they share the height of the page.

Views are keyed by view type (`scatterplot`, `spatial`, `heatmap`, `violin`,
`dotplot`, `obs_sets`, `feature_list`, …; the full list is `VIEW_MAPPING` in
[build.py](../../src/cellxpatient/build.py)). Each dataset listed under a view
gets its own copy of that view, so a template has at most one view of each type
per dataset. The scatterplot always shows the embedding named `UMAP`. Optional
`props` are passed to the view as they are.

A view's position is either `grid_xywh` at the view level, shifted by each
dataset's `grid_offset_xy`, or a `grid_xywh` per dataset under the view's
`datasets`. The view-level grid takes precedence.

#### Coordination

Defines how views interact and update together. This is the trickiest part of a
Vitessce configuration.

A coordination type is a property that can be coordinated, such as
`featureSelection`, `obsSetSelection` or `obsColorEncoding`. Not every view
supports every coordination type, and each type expects values of a given form;
see the
[Vitessce coordination documentation](https://vitessce.io/docs/coordination-types/#initial-coordination-values).

For each coordination type, one or more coordination scopes can exist. Views
referencing the same scope share the state of that coordination type:

- view_1: coord_type_A → scope_1
- view_2: coord_type_A → scope_1
- view_3: coord_type_A → scope_2

Here, view_1 and view_2 are coordinated for coord_type_A, while view_3 is
independent.

In the template, each coordination space lists `datasets`, `views` and `values`.
For each coordination type under `values`, `build.py` creates one scope with
that initial value and links every listed view of every listed dataset to it.

Spatial views need additional hierarchical coordination for individual image and
segmentation layers, set under `per_layer`: `image_layer`, and
`segmentation_layer` with a `cell_channel` and a `nucleus_channel`. The image
layer has its own `values` and `views`; the segmentation layer has its `views`,
and each channel its own `values`. A segmentation channel can also reuse the
space's scopes: `inherit: true` links it to all of them, and
`inherit_values: [...]` only to the listed coordination types. An inherited
scope takes precedence over a value of the same type in the channel's own
`values`.

The spatial example uses this to display the morphology image together with cell
and nucleus boundaries, while linking the cell segmentation to the selected gene
expression.

#### Custom

Optional. Its content is merged as is into the top level of the generated
config. `clxpt serve` reads `app.height` from it as the height of the page (1200
pixels by default).

### Example: spatial view

A spatial view coordinating multi-layer spatial data with gene expression.

**Data:** the Xenium 0OE1 example dataset provided by Antonin Thiebault.

**Template:**
[xenium_0OE1_example_template.yaml](../../data/processed/xenium_0OE1_example_template.yaml)

Layout and coordination scopes. Scope A is the template's `global` coordination
space (observation and feature types, gene selection, colour encoding, colour
map range and cell set selection), which the cell boundaries inherit. Scopes B
and C are the own values of the nucleus boundaries and of the image layer.

<table>
  <tr>
    <th></th>
    <th>Columns 1-2</th>
    <th>Columns 3-7</th>
    <th>Columns 8-12</th>
  </tr>
  <tr>
    <td>Row 1</td>
    <td>Description</td>
    <td rowspan="3">Spatial view (Scope A for cell/gene; Scope B for nucleus layer; Scope C for image layer)</td>
    <td rowspan="3">Scatterplot UMAP (Scope A for cell/gene)</td>
  </tr>
  <tr>
    <td>Row 2</td>
    <td>Status</td>
  </tr>
  <tr>
    <td>Rows 3-4</td>
    <td>Layer controller (Scopes A, B, C)</td>
  </tr>
  <tr>
    <td>Rows 5-6</td>
    <td>Cell Sets (Scope A for cell)</td>
    <td rowspan="2">Heatmap (Scope A for cell/gene)</td>
    <td rowspan="2">Gene-linked Violin Plot (Scope A for cell/gene)</td>
  </tr>
  <tr>
    <td>Rows 7-8</td>
    <td>Feature List (Scope A for gene)</td>
  </tr>
</table>
