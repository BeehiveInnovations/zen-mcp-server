"""Thread-safe credential management for Google Cloud with automatic refresh."""

import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

from google.auth import default
from google.auth.credentials import Credentials
from google.auth.exceptions import DefaultCredentialsError, RefreshError
from google.auth.transport.requests import Request

logger = logging.getLogger(__name__)


class CredentialManager:
    """Thread-safe manager for Google Cloud credentials with automatic refresh."""

    def __init__(self, refresh_threshold_minutes: int = 45):
        """Initialize credential manager.

        Args:
            refresh_threshold_minutes: Minutes before expiry to trigger refresh
        """
        self._credentials: Optional[Credentials] = None
        self._project_id: Optional[str] = None
        self._lock = threading.RLock()
        self._last_refresh: Optional[datetime] = None
        self._refresh_threshold = timedelta(minutes=refresh_threshold_minutes)

    def get_credentials(self) -> tuple[Credentials, Optional[str]]:
        """Get valid credentials, refreshing if necessary.

        Returns:
            Tuple of (credentials, project_id)

        Raises:
            ValueError: If credentials cannot be obtained
        """
        with self._lock:
            if self._credentials is None:
                self._initialize_credentials()

            if self._should_refresh():
                self._refresh_credentials()

            return self._credentials, self._project_id

    def get_access_token(self) -> str:
        """Get valid access token.

        Returns:
            Access token string

        Raises:
            ValueError: If token cannot be obtained
        """
        credentials, _ = self.get_credentials()

        if not hasattr(credentials, "token") or not credentials.token:
            raise ValueError("No access token available")

        return credentials.token

    def _initialize_credentials(self):
        """Initialize credentials from environment."""
        try:
            self._credentials, self._project_id = default()
            self._last_refresh = datetime.now()
            logger.info("Google Cloud credentials initialized successfully")
        except DefaultCredentialsError as e:
            logger.error(f"Failed to get default credentials: {e}")
            raise ValueError(
                "Google Cloud credentials not found. Please run 'gcloud auth application-default login' "
                "or set GOOGLE_APPLICATION_CREDENTIALS environment variable."
            )

    def _should_refresh(self) -> bool:
        """Check if credentials should be refreshed.

        Returns:
            True if refresh is needed
        """
        if not hasattr(self._credentials, "expired"):
            return False

        # Check if expired
        if self._credentials.expired:
            return True

        # Check if approaching expiry
        if hasattr(self._credentials, "expiry") and self._credentials.expiry:
            time_until_expiry = self._credentials.expiry - datetime.now()
            if time_until_expiry < self._refresh_threshold:
                return True

        # Check if we haven't refreshed in a while (fallback)
        if self._last_refresh:
            time_since_refresh = datetime.now() - self._last_refresh
            if time_since_refresh > timedelta(hours=1):
                return True

        return False

    def _refresh_credentials(self):
        """Refresh credentials if needed."""
        try:
            # Double-check if another thread already refreshed
            if not self._should_refresh():
                return

            logger.debug("Refreshing Google Cloud credentials")
            self._credentials.refresh(Request())
            self._last_refresh = datetime.now()
            logger.debug("Credentials refreshed successfully")

        except RefreshError as e:
            logger.error(f"Failed to refresh credentials: {e}")
            # Re-initialize credentials as fallback
            self._initialize_credentials()

    def close(self):
        """Clean up resources."""
        # Currently no cleanup needed, but provided for future use
        pass
