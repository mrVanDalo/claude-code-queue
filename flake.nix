{
  description = "Queue Claude Code prompts and execute them when token limits reset";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        claude-code-queue = pkgs.python3Packages.buildPythonApplication rec {
          pname = "claude-code-queue";
          version = "0.1.3";
          pyproject = true;

          src = ./.;

          build-system = with pkgs.python3Packages; [
            setuptools
          ];

          dependencies = with pkgs.python3Packages; [
            pyyaml
          ];

          pythonImportsCheck = [ "claude_code_queue" ];

          meta = {
            description = "Queue Claude Code prompts and execute them when token limits reset";
            homepage = "https://github.com/JCSnap/claude-code-queue";
            license = pkgs.lib.licenses.mit;
            maintainers = [ ];
            mainProgram = "claude-queue";
          };
        };

      in {
        packages = {
          default = claude-code-queue;
          claude-code-queue = claude-code-queue;
        };

        apps.default = {
          type = "app";
          program = "${claude-code-queue}/bin/claude-queue";
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            # Python and build tools
            python3
            python3Packages.setuptools
            python3Packages.pip
            python3Packages.pyyaml

            # Development tools
            python3Packages.black
            python3Packages.flake8
            python3Packages.mypy
            python3Packages.pytest

            # Nix tools
            nixpkgs-fmt
          ];

          shellHook = ''
            echo "🚀 claude-code-queue development environment"
            echo "Python: $(python --version)"
            echo ""
            echo "Available commands:"
            echo "  python -m pip install -e .  # Install in editable mode"
            echo "  claude-queue --help         # Run the CLI"
            echo "  nix build                   # Build the package"
            echo "  nix run                     # Run the package"
            echo ""
          '';
        };
      }
    );
}
