import os
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

print("ENV path:", BASE_DIR / ".env")
print("API KEY LOADED:", bool(os.getenv("OPENAQ_API_KEY")))

"""
env_file = BASE_DIR / ".env"

print("ENV EXISTS:", env_file.exists())
print("ENV CONTENT:")
print(env_file.read_text())
"""

def get_env(name: str) -> str:
    # Read required env variable
    value = os.getenv(name)

    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")

    return value

OPENAQ_API_KEY = get_env("OPENAQ_API_KEY")

DB_USER = get_env("DB_USER")
DB_PASSWORD = get_env("DB_PASSWORD")
DB_HOST = get_env("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = get_env("DB_NAME")

DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
