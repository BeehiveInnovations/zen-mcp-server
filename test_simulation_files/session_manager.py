#!/usr/bin/env python3
import json
from datetime import datetime, timedelta

class SessionManager:
    def __init__(self):
        self.active_sessions = {}
        self.session_timeout = 30 * 60  # 30 minutes in seconds

    def create_session(self, user_id, user_data):
        """Create a new user session"""
        session_id = f"sess_{user_id}_{datetime.now().timestamp()}"

        session_info = {
            'user_id': user_id,
            'user_data': user_data,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(seconds=self.session_timeout)
        }

        self.active_sessions[session_id] = session_info
        return session_id

    def validate_session(self, session_id):
        """Check if session is valid and not expired"""
        if session_id not in self.active_sessions:
            return False

        session = self.active_sessions[session_id]
        current_time = datetime.now()

        # Check if session has expired
        if current_time > session['expires_at']:
            del self.active_sessions[session_id]
            return False

        return True

    def cleanup_expired_sessions(self):
        """Remove expired sessions from memory"""
        current_time = datetime.now()
        expired_count = 0

        # BUG: Modifying dictionary while iterating over it
        for session_id, session in self.active_sessions.items():
            if current_time > session['expires_at']:
                del self.active_sessions[session_id]  # This causes RuntimeError
                expired_count += 1

        return expired_count
