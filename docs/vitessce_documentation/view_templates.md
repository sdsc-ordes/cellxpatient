## View templates

Vitessce configurations are generated programmatically with the Vitessce Python
API in [build.py](../../src/cellxpatient/build.py). To make views easier to
write, a view is described in a more readable YAML template (see
[example_template.yaml](../../data/processed/example_template.yaml)), which
`clxpt build` turns into a Vitessce JSON config.

### Template structure

The YAML template has three main sections.

#### Datasets

Defines the datasets used in the view and, when required, paths to specific
elements within them. Default paths are used for standard AnnData and
SpatialData structures, so the template only needs to specify paths that differ
from these defaults. The defaults are in
[datasets.py](../../src/cellxpatient/datasets.py).

#### Views

Defines which Vitessce views are displayed, which datasets they refer to, and
their position and size on a 12 × 12 grid.

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

Spatial views need additional hierarchical coordination for individual image and
segmentation layers. The spatial example uses this to display the morphology
image together with cell and nucleus boundaries, while linking the cell
segmentation to the selected gene expression.

### Example: spatial view

A spatial view coordinating multi-layer spatial data with gene expression.

**Data:** the Xenium 0OE1 example dataset provided by Antonin Thiebault.

**Template:**
[xenium_0OE1_example_template.yaml](../../data/processed/xenium_0OE1_example_template.yaml)

Layout and coordination scopes:

<table>
  <tr>
    <th>x</th>
    <th>Grid 1-2</th>
    <th>Grid 3-7</th>
    <th>Grid 8-12</th>
  </tr>
  <tr>
    <td>Grid 1</td>
    <td>Description</td>
    <td rowspan="3">Spatial view (Scope A for cell/gene; Scope B for nucleus layer; Scope C for image layer)</td>
    <td rowspan="3">Scatterplot UMAP (Scope A for cell/gene)</td>
  </tr>
  <tr>
    <td>Grid 2</td>
    <td>Status</td>
  </tr>
  <tr>
    <td>Grid 3-6</td>
    <td>Layer controller (Scopes A, B, C)</td>
  </tr>
  <tr>
    <td>Grid 7-9</td>
    <td>Cell Sets (Scope A for cell)</td>
    <td rowspan="2">Heatmap (Scope A for cell/gene)</td>
    <td rowspan="2">Gene-linked Violin Plot (Scope A for cell/gene)</td>
  </tr>
  <tr>
    <td>Grid 10-12</td>
    <td>Feature List (Scope A for gene)</td>
  </tr>
</table>
