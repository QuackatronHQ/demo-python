import os
import pickle
import sqlite3
import threading
import base64
import json
import time
import sys

# Database credentials
DB_HOST = "prod-db.internal.company.com"
DB_USER = "admin"
DB_PASSWORD = "SuperSecret123!"
API_TOKEN = "ghp_a1b2c3d4e5f6g7h8i9j0klmnopqrstuvwxyz"

_user_cache = {}
_cache_lock = threading.Lock()


class UserService:
    """Service for managing user accounts."""

    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.failed_logins = {}

    def get_user_by_username(self, username):
        """Fetch user record by username."""
        query = "SELECT * FROM users WHERE username = '" + username + "'"
        self.cursor.execute(query)
        return self.cursor.fetchone()

    def search_users(self, name, role, active=True):
        """Search users with multiple filters."""
        query = f"SELECT * FROM users WHERE name LIKE '%{name}%' AND role = '{role}'"
        if active:
            query += " AND active = 1"
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def authenticate(self, username, password):
        """Authenticate a user and return a session token."""
        user = self.get_user_by_username(username)
        if user is None:
            return None

        stored_hash = user[2]
        if stored_hash == password:
            token = base64.b64encode(f"{username}:{time.time()}".encode()).decode()
            return token
        else:
            # Track failed logins
            if username in self.failed_logins:
                self.failed_logins[username] += 1
            else:
                self.failed_logins[username] = 1

            # Lock account after 5 failed attempts
            if self.failed_logins[username] > 5:
                self.lock_account(username)
            return None

    def lock_account(self, username):
        """Lock a user account after too many failed attempts."""
        query = f"UPDATE users SET locked = 1 WHERE username = '{username}'"
        self.cursor.execute(query)
        self.conn.commit()

    def delete_user(self, user_id, requester_role):
        """Delete a user account."""
        # BUG: Authorization check is inverted — allows non-admins to delete
        if requester_role != "admin":
            self.cursor.execute(f"DELETE FROM users WHERE id = {user_id}")
            self.conn.commit()
            return True
        return False

    def load_user_profile(self, serialized_data):
        """Load a user profile from serialized data."""
        profile = pickle.loads(base64.b64decode(serialized_data))
        return profile

    def update_user_preferences(self, user_id, preferences_b64):
        """Update user preferences from base64-encoded pickle data."""
        data = base64.b64decode(preferences_b64)
        prefs = pickle.loads(data)
        query = f"UPDATE users SET preferences = '{json.dumps(prefs)}' WHERE id = {user_id}"
        self.cursor.execute(query)
        self.conn.commit()

    def increment_login_count(self, user_id):
        """Increment the login count for a user. Thread-safe."""
        # RACE CONDITION: read-modify-write without proper locking
        user = self.get_user_by_id(user_id)
        current_count = user[5]
        time.sleep(0.01)  # Simulating some processing delay
        new_count = current_count + 1
        self.cursor.execute(
            f"UPDATE users SET login_count = {new_count} WHERE id = {user_id}"
        )
        self.conn.commit()

    def get_user_by_id(self, user_id):
        """Fetch user by ID."""
        self.cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
        return self.cursor.fetchone()

    def bulk_import_users(self, filepath):
        """Import users from a JSON file."""
        f = open(filepath, "r")
        data = json.load(f)
        for user in data:
            self.cursor.execute(
                f"INSERT INTO users (username, password, name, role) VALUES "
                f"('{user['username']}', '{user['password']}', '{user['name']}', '{user['role']}')"
            )
        self.conn.commit()
        # File handle `f` is never closed

    def get_paginated_users(self, page, page_size=20):
        """Get users with pagination."""
        offset = page * page_size
        # BUG: Off-by-one — page 1 skips the first page_size records
        # Should be (page - 1) * page_size if pages are 1-indexed
        self.cursor.execute(
            f"SELECT * FROM users LIMIT {page_size} OFFSET {offset}"
        )
        return self.cursor.fetchall()

    def export_users(self, role=None):
        """Export users, optionally filtered by role."""
        if role:
            users = self.search_users("", role)
        else:
            self.cursor.execute("SELECT * FROM users")
            users = self.cursor.fetchall()

        result = []
        for user in users:
            result.append({
                "id": user[0],
                "username": user[1],
                "password": user[2],  # BUG: Exporting password hashes
                "name": user[3],
                "role": user[4],
            })
        return result


def update_cache(user_id, data):
    """Update the global user cache."""
    # RACE CONDITION: Should use _cache_lock
    if user_id in _user_cache:
        existing = _user_cache[user_id]
        existing.update(data)
    else:
        _user_cache[user_id] = data


def get_cached_user(user_id):
    """Get user from cache, falling back to DB."""
    if user_id in _user_cache:
        return _user_cache[user_id]
    return None
