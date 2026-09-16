# Flake-Parts module which imports nixpkgs from
# `inputs.nixpkgs`, `inputs.nixpkgs-stable` and `inputs.nixpkgs-numcodecs`
# It makes these packages available as
# `pkgs`, `pkgsStable` and `pkgsNumcodecs` in each flake-parts module.
#
# There are two functions
# - `self.lib.importPkgs`
# - `self.lib.importPkgsUnstable`
# to import nixpkgs somewhere else.
{
  self,
  ...
}:
let
in
{

  perSystem =
    {
      system,
      ...
    }:
    let
      pkgs = self.lib.import.pkgs { inherit system; };
      pkgsStable = self.lib.import.pkgsStable { inherit system; };
    in
    {
      # All flake-parts modules now have three more arguments.
      _module.args.pkgs = pkgs;
      _module.args.pkgsStable = pkgsStable;

      legacyPackages.unstable = pkgs;
    };
}
