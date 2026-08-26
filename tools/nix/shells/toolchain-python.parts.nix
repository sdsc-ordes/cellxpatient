{
  ...
}:
{
  perSystem =
    { lib, pkgs, ... }:
    {
      toolchains.cirrocumulus = [
        {
          packages = [
            # Language Server.
            pkgs.pyright

            pkgs.stdenv.cc.cc.lib # fix: libstdc++ required by jupyter.
            pkgs.zlib # fix: for numpy/pandas import
          ];

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

          env = {
            RUFF_CACHE_DIR = ".output/cache/ruff";
          };

          env.LD_LIBRARY_PATH = "${lib.makeLibraryPath [
            pkgs.stdenv.cc.cc.lib
            pkgs.zlib
          ]}";
        }
      ];
    };
}
