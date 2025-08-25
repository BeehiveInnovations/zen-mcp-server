{
  description = "Zen MCP Server";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs { inherit system; };
      python = pkgs.python312;
    in {
      packages.default = python.pkgs.buildPythonApplication {
        pname = "zen-mcp-server";
        version = "1.1.0";
        src = ./.;
        format = "pyproject";

        nativeBuildInputs = with python.pkgs; [
          setuptools
          setuptools-scm
          wheel
        ];
        propagatedBuildInputs = with python.pkgs; [
          mcp google-genai openai pydantic python-dotenv
        ];

        # If packages aren't in nixpkgs, override here
        # postInstall = "ln -s $out/bin/server.py $out/bin/zen-mcp-server";
      };

      devShells.default = pkgs.mkShell {
        packages = [
          python
          python.pkgs.pip
          python.pkgs.virtualenv
          # Basic tools
          pkgs.git
        ] ++ (with python.pkgs; [
          # Only basic packages from nixpkgs
          pytest pytest-mock black ruff isort setuptools wheel
        ]);

        shellHook = ''
          if [ ! -d ".nix-venv" ]; then
            echo "Setting up Python environment..."
            python -m venv .nix-venv --quiet
            source .nix-venv/bin/activate
            pip install -q --upgrade pip
            pip install -q -e .
            pip install -q pytest-asyncio python-semantic-release
            deactivate
          fi
          source .nix-venv/bin/activate
        '';

        # Ensure proper shared library paths
        LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
          pkgs.stdenv.cc.cc.lib
        ];
      };
    });
}
