{ inputs, ... }:
{
  imports = [ inputs.treefmt-nix.flakeModule ];

  perSystem = _: {
    treefmt = {
      projectRootFile = "flake.nix";

      programs = {
        # Python formatting with black
        black.enable = true;

        # Python import sorting
        isort.enable = true;

        # Nix formatting
        nixpkgs-fmt.enable = true;

        # Markdown formatting
        mdformat.enable = true;
      };

      settings.formatter = {
        black = {
          options = [ "--line-length" "88" ];
          includes = [ "*.py" ];
        };

        isort = {
          options = [ "--profile" "black" ];
          includes = [ "*.py" ];
        };

        nixpkgs-fmt = {
          includes = [ "*.nix" ];
        };

        mdformat = {
          includes = [ "*.md" ];
          excludes = [ "CLAUDE.md" ];
        };
      };
    };
  };
}
