import os

# ============================================================
# PERSONAL CONFIGURATION - Change these to your own values!
# ============================================================

# Your names (displayed on the landing page)
PARTNER_1 = "Him"
PARTNER_2 = "Her"

# Relationship start date (YYYY-MM-DD format)
RELATIONSHIP_START = "2024-01-01"

# Login password (both of you use this to access the site)
SITE_PASSWORD = "ourlove2024"

# ============================================================
# TECHNICAL CONFIGURATION
# ============================================================

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-to-a-random-secret-string")
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads")
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "loving.db")
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max upload

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "heic"}
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "avi", "webm", "mkv"}
