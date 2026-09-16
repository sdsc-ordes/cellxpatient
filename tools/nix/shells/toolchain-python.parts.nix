{
  ...
}:
{
  perSystem =
    { lib, pkgs, ... }:
    {

      toolchains.common = [
        {
          packages = [
            # Language Server.
            pkgs.pyright

            # Git
            pkgs.git

            pkgs.stdenv.cc.cc.lib # fix: libstdc++ required by jupyter.
            pkgs.zlib # fix: for numpy/pandas import
          ];

          env = {
            RUFF_CACHE_DIR = ".output/cache/ruff";
          };

          env.LD_LIBRARY_PATH = "${lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
            pkgs.zlib
          ]}";
        }
      ];

      toolchains.vitessce = [
        {
          # We use `devenv` language support since, it's
          # pretty involved to setup a python environment.
          languages.python = {
            enable = true;
            venv.enable = true;

            # Heavy modules relying (CYTHON, ext. shared libraries etc)
            # should be built by Nix.
            package = pkgs.python312.withPackages (p: [
              p.numpy
              p.matplotlib
            ]);

            uv = {
              enable = true;
              package = pkgs.uv;
              sync.enable = true;
            };
          };
        }
      ];

      toolchains.mdv = [
        {
          # We use `devenv` language support since, it's
          # pretty involved to setup a python environment.
          languages.python = {
            enable = true;
            venv.enable = true;

            # Heavy modules relying (CYTHON, ext. shared libraries etc)
            # should be built by Nix.
            package = pkgs.python312.withPackages (p: [
              p.numpy
              p.matplotlib
            ]);

            uv = {
              enable = true;
              package = pkgs.uv;
              sync.enable = true;
            };
          };
        }
      ];

      toolchains.cirrocumulus = [
        {
          # We use `devenv` language support since, it's
          # pretty involved to setup a python environment.
          languages.python = {
            enable = true;

            # Heavy modules relying (CYTHON, ext. shared libraries etc)
            # should be built by Nix.
            package = pkgs.python312.withPackages (p: [
              p.numpy
              p.matplotlib
            ]);

            venv = {
              enable = true;
              requirements = ''
                cirrocumulus
                typing-extensions
                numcodecs==0.15.1
              '';
            };
          };
        }
      ];
    };
}
