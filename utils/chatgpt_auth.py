"""Simple ChatGPT authentication utility."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ChatGPTAuth:
    """ChatGPT authentication data."""

    access_token: str
    account_id: str
    refresh_token: str
    id_token: str
    last_refresh: str

    def is_valid(self) -> bool:
        """Check if auth has required tokens."""
        return bool(self.access_token and self.account_id)


def get_chatgpt_auth() -> Optional[ChatGPTAuth]:
    """Get auth data from ~/.codex/auth.json if available."""
    try:
        auth_file = Path.home() / ".codex" / "auth.json"
        if not auth_file.exists():
            return None

        with open(auth_file) as f:
            data = json.load(f)

        tokens = data.get("tokens", {})
        return ChatGPTAuth(
            access_token=tokens.get("access_token", ""),
            account_id=tokens.get("account_id", ""),
            refresh_token=tokens.get("refresh_token", ""),
            id_token=tokens.get("id_token", ""),
            last_refresh=data.get("last_refresh", ""),
        )
    except Exception:
        return None


def is_chatgpt_mode_enabled() -> bool:
    """Check if OPENAI_CHATGPT_LOGIN_MODE=true."""
    return os.getenv("OPENAI_CHATGPT_LOGIN_MODE", "").lower() == "true"


def get_valid_chatgpt_auth() -> Optional[ChatGPTAuth]:
    """Get valid ChatGPT auth if mode is enabled and tokens exist."""
    if not is_chatgpt_mode_enabled():
        return None

    auth = get_chatgpt_auth()
    return auth if auth and auth.is_valid() else None
