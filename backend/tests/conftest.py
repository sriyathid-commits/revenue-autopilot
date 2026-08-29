import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from backend.config import get_settings

get_settings.cache_clear()
