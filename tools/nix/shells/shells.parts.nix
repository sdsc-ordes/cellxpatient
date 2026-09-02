{
  self,
  inputs,
  lib,
  ...
}:
{
  perSystem =
    {
      self',
      config,
      ...
    }:
    let
      args = config.allModuleArgs; # See https://flake.parts/module-arguments#obtaining-all-module-arguments
      toolchains = config.toolchains;
      language = "generic";
    in
    {
      devShells.default = self.lib.shell.mkShell {
        inherit (args) system;
        modules = toolchains.general ++ toolchains.${language};
      };

      devShells.changelog = self.lib.shell.mkShell {
        inherit (args) system;
        modules = toolchains.changelog;
      };

      devShells.format = self.lib.shell.mkShell {
        inherit (args) system;
        modules = toolchains.format;
      };

      devShells.cirrocumulus = self.lib.shell.mkShell {
        inherit (args) system;
        subRootdir = "./cirrocumulus_test";
        modules = toolchains.cirrocumulus ++ toolchains.common;
      };

      devShells.mdv = self.lib.shell.mkShell {
        inherit (args) system;
        subRootdir = "./mdv_test";
        modules = toolchains.mdv ++ toolchains.common;
      };

      devShells.vitessce = self.lib.shell.mkShell {
        inherit (args) system;
        subRootdir = "./vitessce_test";
        modules = toolchains.vitessce ++ toolchains.common;
      };

      # The CI shell is the same as the default.
      devShells.ci = self'.devShells.default;
    };
}
