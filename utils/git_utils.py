"""
Git utilities for finding repositories and generating diffs.
"""

import subprocess
from typing import Dict, List, Tuple
from pathlib import Path


# Directories to ignore when searching for git repositories
IGNORED_DIRS = {
    "node_modules",
    "__pycache__",
    "venv",
    "env",
    "build",
    "dist",
    "target",
    ".tox",
    ".pytest_cache",
}


def find_git_repositories(start_path: str, max_depth: int = 5) -> List[str]:
    """
    Recursively find all git repositories starting from the given path.

    Args:
        start_path: Directory to start searching from
        max_depth: Maximum depth to search (prevents excessive recursion)

    Returns:
        List of absolute paths to git repositories
    """
    repositories = []
    start_path = Path(start_path).resolve()

    def _find_repos(current_path: Path, current_depth: int):
        if current_depth > max_depth:
            return

        try:
            # Check if current directory is a git repo
            git_dir = current_path / ".git"
            if git_dir.exists() and git_dir.is_dir():
                repositories.append(str(current_path))
                # Don't search inside .git directory
                return

            # Search subdirectories
            for item in current_path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    # Skip common non-code directories
                    if item.name in IGNORED_DIRS:
                        continue
                    _find_repos(item, current_depth + 1)

        except PermissionError:
            # Skip directories we can't access
            pass

    _find_repos(start_path, 0)
    return sorted(repositories)


def run_git_command(repo_path: str, command: List[str]) -> Tuple[bool, str]:
    """
    Run a git command in the specified repository.

    Args:
        repo_path: Path to the git repository
        command: Git command as a list of arguments

    Returns:
        Tuple of (success, output/error)
    """
    try:
        result = subprocess.run(
            ["git"] + command, cwd=repo_path, capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr

    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def get_git_status(repo_path: str) -> Dict[str, any]:
    """
    Get the current git status of a repository.

    Args:
        repo_path: Path to the git repository

    Returns:
        Dictionary with status information
    """
    status = {
        "branch": "",
        "ahead": 0,
        "behind": 0,
        "staged_files": [],
        "unstaged_files": [],
        "untracked_files": [],
    }

    # Get current branch
    success, branch = run_git_command(repo_path, ["branch", "--show-current"])
    if success:
        status["branch"] = branch.strip()

    # Get ahead/behind info
    if status["branch"]:
        success, ahead_behind = run_git_command(
            repo_path,
            [
                "rev-list",
                "--count",
                "--left-right",
                f'{status["branch"]}@{{upstream}}...HEAD',
            ],
        )
        if success:
            if ahead_behind.strip():
                parts = ahead_behind.strip().split()
                if len(parts) == 2:
                    status["behind"] = int(parts[0])
                    status["ahead"] = int(parts[1])
        # else: Could not get ahead/behind status (branch may not have upstream)

    # Get file status
    success, status_output = run_git_command(repo_path, ["status", "--porcelain"])
    if success:
        for line in status_output.strip().split("\n"):
            if not line:
                continue

            status_code = line[:2]
            path_info = line[3:]

            # Handle staged changes
            if status_code[0] == "R":
                # Format is "old_path -> new_path" for renamed files
                if " -> " in path_info:
                    _, new_path = path_info.split(" -> ", 1)
                    status["staged_files"].append(new_path)
                else:
                    status["staged_files"].append(path_info)
            elif status_code[0] in ["M", "A", "D", "C"]:
                status["staged_files"].append(path_info)

            # Handle unstaged changes
            if status_code[1] in ["M", "D"]:
                status["unstaged_files"].append(path_info)
            elif status_code == "??":
                status["untracked_files"].append(path_info)

    return status
