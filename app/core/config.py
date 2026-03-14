from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
REDIS_URL = os.getenv("REDIS_URL")

UNUSED_LINK_DAYS = int(os.getenv("UNUSED_LINK_DAYS", 30))