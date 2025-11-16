#!/usr/bin/env python3
"""
Sync version from pyproject.toml to config.py
This script is called by GitHub Actions after semantic-release updates the version
"""

import re
from datetime import datetime

import toml


def update_config_version():
    # Read version from pyproject.toml
    with open("pyproject.toml") as f:
        data = toml.load(f)
        version = data["project"]["version"]

    # Read current config.py
    with open("config.py") as f:
        content = f.read()

    # Update version
    content = re.sub(r'__version__ = "[^"]*"', f'__version__ = "{version}"', content)

    # Update date to current date
    today = datetime.now().strftime("%Y-%m-%d")
    content = re.sub(r'__updated__ = "[^"]*"', f'__updated__ = "{today}"', content)

    # Write back
    with open("config.py", "w") as f:
        f.write(content)

    print(f"Updated config.py to version {version}")


if __name__ == "__main__":
    update_config_version()
