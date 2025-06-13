#!/usr/bin/env python3
"""
Version bumping utility for Gemini MCP Server

This script handles semantic version bumping for the project by:
- Reading current version from config.py
- Applying the appropriate version bump (major, minor, patch)
- Updating config.py with new version and timestamp
- Preserving file structure and formatting
"""

import re
import sys
from datetime import datetime
from pathlib import Path


def parse_version(version_string: str) -> tuple[int, int, int]:
    """Parse semantic version string into tuple of integers."""
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version_string)
    if not match:
        raise ValueError(f"Invalid version format: {version_string}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_version(version: tuple[int, int, int], bump_type: str) -> tuple[int, int, int]:
    """Apply version bump according to semantic versioning rules."""
    major, minor, patch = version

    if bump_type == "major":
        return (major + 1, 0, 0)
    elif bump_type == "minor":
        return (major, minor + 1, 0)
    elif bump_type == "patch":
        return (major, minor, patch + 1)
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")


def update_config_file(new_version: str) -> None:
    """Update version and timestamp in config.py while preserving structure."""
    config_path = Path(__file__).parent.parent / "config.py"

    if not config_path.exists():
        raise FileNotFoundError(f"config.py not found at {config_path}")

    # Read the current content
    content = config_path.read_text()

    # Update version using regex to preserve formatting
    version_pattern = r'(__version__\s*=\s*["\'])[\d\.]+(["\'])'
    content = re.sub(version_pattern, rf"\g<1>{new_version}\g<2>", content)

    # Update the __updated__ field with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    updated_pattern = r'(__updated__\s*=\s*["\'])[\d\-]+(["\'])'
    content = re.sub(updated_pattern, rf"\g<1>{current_date}\g<2>", content)

    # Write back the updated content
    config_path.write_text(content)
    print(f"Updated config.py: version={new_version}, updated={current_date}")


def get_current_version() -> str:
    """Extract current version from config.py."""
    config_path = Path(__file__).parent.parent / "config.py"

    if not config_path.exists():
        raise FileNotFoundError(f"config.py not found at {config_path}")

    content = config_path.read_text()
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)

    if not match:
        raise ValueError("Could not find __version__ in config.py")

    return match.group(1)


def main():
    """Main entry point for version bumping."""
    if len(sys.argv) != 2:
        print("Usage: python bump_version.py <major|minor|patch>")
        sys.exit(1)

    bump_type = sys.argv[1].lower()
    if bump_type not in ["major", "minor", "patch"]:
        print(f"Invalid bump type: {bump_type}")
        print("Valid types: major, minor, patch")
        sys.exit(1)

    try:
        # Get current version
        current = get_current_version()
        print(f"Current version: {current}")

        # Parse and bump version
        version_tuple = parse_version(current)
        new_version_tuple = bump_version(version_tuple, bump_type)
        new_version = f"{new_version_tuple[0]}.{new_version_tuple[1]}.{new_version_tuple[2]}"

        # Update config file
        update_config_file(new_version)

        # Output new version for GitHub Actions
        print(f"New version: {new_version}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
