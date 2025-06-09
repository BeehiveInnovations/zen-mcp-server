"""
Setup configuration for Gemini MCP Server
"""

from pathlib import Path

from setuptools import setup

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

setup(
    name="gemini-mcp-server",
    version="2.7.0",
    description="Model Context Protocol server for Google Gemini",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Fahad Gilani",
    python_requires=">=3.10",
    py_modules=["gemini_server"],
    install_requires=[
        "mcp>=1.0.0",
        "google-genai>=1.19.0",
        "python-dotenv>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-mock>=3.11.0",
        ]
    },
    entry_points={
        "console_scripts": [
            "gemini-mcp-server=gemini_server:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
