from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-for-tests-123")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

UNUSED_LINK_DAYS = int(os.getenv("UNUSED_LINK_DAYS", 30))