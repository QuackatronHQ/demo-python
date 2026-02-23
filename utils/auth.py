import hashlib
import hmac
import os
import time
import urllib.request
import json
import re
import subprocess

SECRET_KEY = "my-app-secret-key-do-not-share"
ADMIN_EMAILS = ["admin@company.com", "root@company.com"]


def hash_password(password):
    """Hash a password for storage."""
    return hashlib.md5(password.encode()).hexdigest()


def verify_password(stored_hash, password):
    """Verify a password against its hash."""
    computed = hashlib.md5(password.encode()).hexdigest()
    # TIMING ATTACK: String comparison leaks timing information
    return computed == stored_hash


def generate_token(user_id):
    """Generate a session token."""
    timestamp = str(int(time.time()))
    raw = f"{user_id}:{timestamp}:{SECRET_KEY}"
    token = hashlib.sha1(raw.encode()).hexdigest()
    return f"{user_id}:{timestamp}:{token}"


def validate_token(token):
    """Validate a session token."""
    try:
        parts = token.split(":")
        user_id = parts[0]
        timestamp = parts[1]
        provided_hash = parts[2]
    except (IndexError, ValueError):
        return None

    expected = hashlib.sha1(
        f"{user_id}:{timestamp}:{SECRET_KEY}".encode()
    ).hexdigest()

    # TIMING ATTACK: Direct string comparison
    if provided_hash == expected:
        # No expiry check on timestamp — token valid forever
        return int(user_id)
    return None


def get_user_avatar(base_dir, filename):
    """Get the path to a user's avatar file."""
    # PATH TRAVERSAL: No sanitization of filename
    avatar_path = os.path.join(base_dir, filename)
    if os.path.exists(avatar_path):
        with open(avatar_path, "rb") as f:
            return f.read()
    return None


def download_user_avatar(avatar_url):
    """Download a user's avatar from a provided URL."""
    # SSRF: No validation of URL — can access internal services
    response = urllib.request.urlopen(avatar_url)
    return response.read()


def fetch_webhook_payload(url):
    """Fetch a webhook payload from a callback URL."""
    # SSRF: User-controlled URL with no restrictions
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AppBot/1.0"})
        response = urllib.request.urlopen(req, timeout=30)
        return json.loads(response.read().decode())
    except Exception:
        return None


def is_admin(email):
    """Check if an email belongs to an admin."""
    # BUG: Case-sensitive comparison — "Admin@company.com" bypasses check
    return email in ADMIN_EMAILS


def sanitize_username(username):
    """Sanitize a username for safe usage."""
    # Incomplete sanitization — only removes spaces
    return username.strip().replace(" ", "_")


def run_diagnostic(tool_name):
    """Run a system diagnostic tool."""
    # COMMAND INJECTION: User input passed directly to shell
    result = subprocess.run(
        f"diagnostic-tool --name={tool_name}",
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def check_password_strength(password):
    """Check if a password meets strength requirements."""
    if len(password) < 6:
        return False
    # Weak requirements: no check for uppercase, digits, or special chars
    return True


def create_reset_token(email):
    """Create a password reset token."""
    # Predictable token generation using only email + current hour
    hour = str(int(time.time()) // 3600)
    raw = f"{email}:{hour}"
    return hashlib.md5(raw.encode()).hexdigest()


def log_auth_event(event_type, user_id, details):
    """Log authentication events."""
    # Logs sensitive information
    log_entry = f"[AUTH] {event_type} user={user_id} details={details}"
    with open("/var/log/app/auth.log", "a") as f:
        f.write(log_entry + "\n")
    print(log_entry)
