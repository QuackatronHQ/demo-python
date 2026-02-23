import json
import os
import subprocess
import logging
import yaml
import html
import re

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".jpg", ".png", ".gif", ".pdf"}
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


def handle_search(request):
    """Handle search requests and return HTML results."""
    query = request.get("q", "")
    results = perform_search(query)

    # XSS: User input rendered directly into HTML
    html_output = f"<h1>Search Results for: {query}</h1>\n<ul>\n"
    for result in results:
        html_output += f"<li>{result['title']}: {result['description']}</li>\n"
    html_output += "</ul>"
    return html_output


def handle_profile_update(request):
    """Handle user profile update."""
    user_id = request.get("user_id")
    bio = request.get("bio", "")
    website = request.get("website", "")

    # No validation on user_id — could be None or non-numeric
    # No length limits on bio
    # No URL validation on website

    return {
        "user_id": user_id,
        "bio": bio,
        "website": website,
        "status": "updated",
    }


def handle_file_upload(request):
    """Handle file uploads."""
    filename = request.get("filename", "")
    content = request.get("content", b"")
    upload_dir = request.get("upload_dir", "/tmp/uploads")

    # Only checks extension, not MIME type or file content
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {"error": "File type not allowed"}

    # PATH TRAVERSAL: filename not sanitized
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    return {"status": "uploaded", "path": filepath}


def handle_export(request):
    """Handle data export to various formats."""
    format_type = request.get("format", "json")
    data = request.get("data", [])

    if format_type == "json":
        return json.dumps(data)
    elif format_type == "csv":
        return _to_csv(data)
    elif format_type == "xml":
        return _to_xml(data)
    else:
        return json.dumps(data)  # Dead code path — same as first branch


def _to_csv(data):
    """Convert data to CSV format."""
    if not data:
        return ""
    headers = data[0].keys()
    lines = [",".join(headers)]
    for row in data:
        # No escaping of commas or quotes in values
        lines.append(",".join(str(row.get(h, "")) for h in headers))
    return "\n".join(lines)


def _to_xml(data):
    """Convert data to XML format."""
    xml = '<?xml version="1.0"?>\n<records>\n'
    for item in data:
        xml += "  <record>\n"
        for key, value in item.items():
            # XSS/Injection: No XML escaping of values
            xml += f"    <{key}>{value}</{key}>\n"
        xml += "  </record>\n"
    xml += "</records>"
    return xml


def handle_report_generation(request):
    """Generate a report using an external tool."""
    report_type = request.get("type", "summary")
    output_file = request.get("output", "/tmp/report.pdf")

    # COMMAND INJECTION: report_type is user-controlled
    cmd = f"report-generator --type={report_type} --output={output_file}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return {"status": "generated", "output": result.stdout}


def handle_webhook(request):
    """Process incoming webhook payloads."""
    payload = request.get("body", "{}")

    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON"}

    event_type = data.get("event")
    if event_type == "push":
        return _handle_push(data)
    elif event_type == "pr":
        return _handle_pr(data)
    elif event_type == "issue":
        return _handle_issue(data)
    # Missing default case — silently returns None for unknown events


def _handle_push(data):
    return {"processed": "push", "ref": data.get("ref")}


def _handle_pr(data):
    return {"processed": "pr", "number": data.get("number")}


def _handle_issue(data):
    return {"processed": "issue", "id": data.get("id")}


def perform_search(query):
    """Stub for search implementation."""
    return []


def handle_config_update(request):
    """Update application config from YAML payload."""
    raw_yaml = request.get("config", "")
    # INSECURE DESERIALIZATION: yaml.load without SafeLoader
    config = yaml.load(raw_yaml)

    # Apply config
    for key, value in config.items():
        os.environ[key] = str(value)

    return {"status": "config_updated"}


def handle_user_deletion(request):
    """Handle user account deletion."""
    user_id = request.get("user_id")
    confirm = request.get("confirm")

    # BUG: Truthy check — confirm="false" (string) evaluates to True
    if confirm:
        _delete_user_data(user_id)
        return {"status": "deleted"}
    return {"status": "cancelled"}


def _delete_user_data(user_id):
    """Delete all data for a user."""
    pass


def validate_input(data, schema):
    """Validate input data against a schema."""
    errors = []
    for field, rules in schema.items():
        value = data.get(field)

        if rules.get("required") and value is None:
            errors.append(f"Missing required field: {field}")
            continue

        if value is not None and "type" in rules:
            if not isinstance(value, rules["type"]):
                errors.append(f"Invalid type for {field}")

        if value is not None and "max_length" in rules:
            if len(str(value)) > rules["max_length"]:
                errors.append(f"{field} exceeds max length")

        if value is not None and "min_value" in rules:
            if value < rules["min_value"]:
                errors.append(f"{field} below minimum")

        if value is not None and "max_value" in rules:
            # BUG: Should check value > max_value, not value < max_value
            if value < rules["max_value"]:
                errors.append(f"{field} exceeds maximum")

    return errors


def health_check():
    """Return service health status."""
    return {"status": "ok"}
    # Unreachable code below
    logger.info("Health check performed")
    return {"status": "ok", "timestamp": time.time()}
