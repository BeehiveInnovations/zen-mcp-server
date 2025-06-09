# macOS Setup Instructions for Gemini MCP Server

## Quick Setup (Recommended)

If you've already cloned the repository, simply run:

```bash
cd ~/gemini-mcp-server    # or wherever you cloned it
./setup.sh
```

This will automatically create a virtual environment and install all dependencies.

## Manual Setup Instructions

### 1. Open Terminal and Navigate to Your Project

First, open Terminal (press `⌘ + Space`, type "Terminal", press Enter).

Navigate to where you cloned the gemini-mcp-server:

```bash
# If you cloned to your home directory:
cd ~/gemini-mcp-server

# If you cloned elsewhere, replace with your path:
cd /path/to/gemini-mcp-server
```

**Tip:** You can drag the folder from Finder into Terminal to get the full path!

### 2. Check Your Python Version

Make sure you have Python 3.10 or newer:

```bash
python3 --version
```

If you see Python 3.9 or older, install a newer version:
```bash
# Using Homebrew (recommended):
brew install python@3.10
```

### 3. Create the Virtual Environment

Run this command in your project directory:

```bash
python3 -m venv venv
```

This creates a folder called `venv` in your project directory.

### 4. Activate the Virtual Environment

```bash
source venv/bin/activate
```

You'll see `(venv)` appear at the beginning of your Terminal prompt.

### 5. Install Dependencies

With the virtual environment activated:

```bash
pip install -r requirements.txt
```

## Verifying Your Setup

After setup, you should have:
- A `venv` folder in your gemini-mcp-server directory
- All dependencies installed (no "ModuleNotFoundError")
- The ability to run the server

## Daily Usage

Each time you work with the project:

1. Navigate to the project directory
2. Activate the virtual environment: `source venv/bin/activate`
3. When done, deactivate: `deactivate`

## Troubleshooting

**"python3: command not found"**
- Install Python: `brew install python@3.10`

**"Permission denied" errors**
- Make sure you're in the right directory
- Try: `chmod +x setup.sh` then `./setup.sh`

**Still seeing "ModuleNotFoundError: No module named 'mcp'"**
- Make sure the virtual environment is activated (you should see `(venv)`)
- Re-run: `pip install -r requirements.txt`

## Need Help?

If you're stuck, please share:
1. Your Python version: `python3 --version`
2. Your current directory: `pwd`
3. The exact error message you're seeing