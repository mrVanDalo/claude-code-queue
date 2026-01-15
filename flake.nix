{
  description = "Queue Claude Code prompts and execute them when token limits reset";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    treefmt-nix.url = "github:numtide/treefmt-nix";
    treefmt-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        ./nix/treefmt.nix
      ];

      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];

      perSystem = { config, system, pkgs, ... }:
        let
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
              homepage = "https://github.com/mrVanDalo/claude-code-queue";
              license = pkgs.lib.licenses.mit;
              maintainers = [ ];
              mainProgram = "claude-queue";
            };
          };
        in
        {
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
              python3Packages.pyyaml

              # Development tools
              python3Packages.mypy
              python3Packages.pytest
              python3Packages.pytest-cov
            ];

            shellHook = ''
              echo "🚀 claude-code-queue development environment"
              echo "Python: $(python --version)"
              echo ""
              echo "Available commands:"
              echo "  nix build                   # Build the package"
              echo "  nix run                     # Run the package"
              echo "  nix fmt                     # Format code"
              echo "  mypy src/                   # Type checking"
              echo "  pytest                      # Run tests"
              echo ""
              echo "⚠️  DO NOT use pip install - build with Nix only"
              echo ""
            '';
          };
        };
    };
}
