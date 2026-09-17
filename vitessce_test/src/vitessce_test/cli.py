import argparse
from pathlib import Path

from vitessce_test import build
from vitessce_test import serve
from vitessce_test import preprocess


def existing_file(
    value: str,
) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {path}")
    return path


def existing_path(
    value: str,
) -> Path:
    path = Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Path not found: {path}")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Preprocess a dataset, build a Vitessce config view from a YAML template or "
            "render a Vitessce config view from a JSON view file."
        )
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
        help="Sub-command to execute.",
    )

    preprocess_command = commands.add_parser(
        "preprocess",
        help=(
            "Preprocess a dataset for Vitessce: convert a Xenium output directory to zarr format, "
            "or take a subset of an AnnData dataset. During preprocessing the expression matrix "
            "is stored as CSC sparse matrix for efficiency when rendering. "
            "Output paths should be relative to the data/processed directory."
        ),
    )
    _ = preprocess_command.add_argument(
        "--type",
        choices=["anndata", "xenium"],
        required=True,
        help="Type of the input dataset.",
    )
    _ = preprocess_command.add_argument(
        "--input",
        required=True,
        type=existing_path,
        help="Input dataset (.h5ad or .zarr for anndata, output directory for xenium).",
    )
    _ = preprocess_command.add_argument(
        "--output",
        default=None,
        type=str,
        help=("Output zarr store, to be used as `dataset_path` in view templates. If not provided, "
             "the output path name will be constructed from the input path and the output "
             "will be saved in ./data/processed"),
    )
    _ = preprocess_command.add_argument(
        "--subset",
        nargs=2,
        metavar=("COLUMN", "VALUE"),
        default=None,
        help="For AnnData only: take a subset where the obs column COLUMN equals VALUE.",
    )
    _ = preprocess_command.add_argument(
        "--umap",
        default="analysis/umap/gene_expression_2_components/projection.csv",
        type=str,
        help="For Xenium only: path to the UMAP projection CSV, relative to the Xenium directory.",
    )
    _ = preprocess_command.add_argument(
        "--clusters",
        default="analysis/clustering/gene_expression_graphclust/clusters.csv",
        type=str,
        help="For Xenium only: path to the clusters CSV, relative to the Xenium directory.",
    )
    _ = preprocess_command.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the output if it already exists.",
    )


    build_command = commands.add_parser(
        "build",
        help=(
            "Build a Vitessce config view from a YAML template. The JSON config view will be saved "
            "to the same directory as the template, with the reference 'template' replaced by 'view' if necessary."
        ),
    )
    _ = build_command.add_argument(
        "--template",
        type=existing_file,
        required=True,
        help="Path to the Vitessce view YAML template.",
    )
    _ = build_command.add_argument(
        "--build-only",
        action="store_true",
        help="Whether to build only the view file and not serve it.",
    )
    _ = build_command.add_argument(
        "--port",
        type=int,
        default=8008,
        help="Port to serve the view on.",
    )


    serve_command = commands.add_parser(
        "serve",
        help="Serve a Vitessce config view from a JSON config file.",
    )
    _ = serve_command.add_argument(
        "--config",
        type=existing_file,
        required=True,
        help="Path to the Vitessce view JSON config.",
    )
    _ = serve_command.add_argument(
        "--port",
        type=int,
        default=8008,
        help="Port to serve the view on.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "preprocess":
        if args.type == "anndata":
            preprocess.prepare_anndata(
                source_path = Path(args.input),
                output_path = args.output,
                options = {
                    "subset": args.subset,
                    "overwrite": args.overwrite
                }
            )

        else:
            preprocess.prepare_xenium(
                source_path = Path(args.input),
                output_path = args.output,
                options = {
                    "umap_path": args.umap,
                    "clusters_path": args.clusters,
                    "overwrite": args.overwrite
                }
            )
        return

    if args.command == "build":
        template_path = Path(args.template)
        config_path = build.build_config(template_path)
        if args.build_only:
            return
    else:
        config_path = Path(args.config)

    serve.serve_config(config_path, port=args.port)


if __name__ == "__main__":
    main()
