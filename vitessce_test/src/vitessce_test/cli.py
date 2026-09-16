import argparse
from pathlib import Path

from vitessce_test import build
from vitessce_test import serve


def existing_file(
    value: str,
) -> Path:
    path = Path(value)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"File not found: {path}")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a Vitessce config view from a YAML template or "
            "render a Vitessce config view from a JSON view file."
        )
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
        help="Sub-command to execute.",
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
