{
  description = "Zen MCP Server - AI-powered MCP server with multiple model providers";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    
    pyproject-nix.url = "github:pyproject-nix/pyproject.nix";
    uv2nix.url = "github:pyproject-nix/uv2nix";
    pyproject-build-systems.url = "github:pyproject-nix/build-system-pkgs";
    
    pyproject-nix.inputs.nixpkgs.follows = "nixpkgs";
    uv2nix.inputs.nixpkgs.follows = "nixpkgs";
    pyproject-build-systems.inputs.nixpkgs.follows = "nixpkgs";
    uv2nix.inputs.pyproject-nix.follows = "pyproject-nix";
    pyproject-build-systems.inputs.pyproject-nix.follows = "pyproject-nix";
  };

  outputs = { self, nixpkgs, flake-utils, uv2nix, pyproject-nix, pyproject-build-systems, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        python = pkgs.python312;
        
        workspace = uv2nix.lib.workspace.loadWorkspace {
          workspaceRoot = ./.;
        };
        
        uvLockedOverlay = workspace.mkPyprojectOverlay {
          sourcePreference = "wheel";
        };
        
        customOverrides = final: prev: { };
        
        pythonSet = 
          (pkgs.callPackage pyproject-nix.build.packages { inherit python; })
          .overrideScope (nixpkgs.lib.composeManyExtensions [
            pyproject-build-systems.overlays.default
            uvLockedOverlay
            customOverrides
          ]);
        
        zenMcpServer = pythonSet."zen-mcp-server";
        
        # Use workspace.deps.default which contains the project dependencies
        projectDeps = workspace.deps.default;
        
        appPythonEnv = pythonSet.mkVirtualEnv 
          "zen-mcp-server-env"
          projectDeps;

      in
      {
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "zen-mcp-server";
          version = zenMcpServer.version;
          src = ./.;
          
          nativeBuildInputs = [ pkgs.makeWrapper ];
          buildInputs = [ appPythonEnv ];
          
          installPhase = ''
            mkdir -p $out/bin $out/lib
            
            cp -r tools providers systemprompts utils $out/lib/
            cp server.py config.py $out/lib/
            cp -r conf $out/lib/
            
            makeWrapper ${appPythonEnv}/bin/python $out/bin/zen-mcp-server \
              --add-flags "$out/lib/server.py" \
              --set PYTHONPATH "$out/lib:${appPythonEnv}/${python.sitePackages}" \
              --prefix PATH : ${pkgs.lib.makeBinPath [ pkgs.git ]}
          '';
          
          meta = with pkgs.lib; {
            description = "AI-powered MCP server with multiple model providers";
            homepage = "https://github.com/BeehiveInnovations/zen-mcp-server";
            license = licenses.asl20;
            maintainers = [];
            platforms = platforms.unix;
          };
        };
        
        packages.zen-mcp-server = self.packages.${system}.default;
        
        devShells.default = pkgs.mkShell {
          packages = [
            appPythonEnv
            pkgs.uv
            pkgs.git
            pkgs.black
            pkgs.ruff
            pkgs.isort
            python.pkgs.pytest
          ];
          
          shellHook = ''
            echo "================================================"
            echo "Zen MCP Server Development Environment"
            echo "================================================"
            echo "Python: ${python.version}"
            echo "Project: zen-mcp-server"
            echo ""
            echo "Available commands:"
            echo "  uv lock          - Update lock file"
            echo "  pytest           - Run tests"
            echo "  black .          - Format code"
            echo "  ruff check .     - Lint code"
            echo "  isort .          - Sort imports"
            echo "================================================"
            
            export PYTHONPATH="$PWD:$PYTHONPATH"
          '';
        };
        
        apps.default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/zen-mcp-server";
        };
      });
}