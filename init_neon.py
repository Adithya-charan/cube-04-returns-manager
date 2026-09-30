import os
from dotenv import load_dotenv
load_dotenv()
from src.db_config import init_db

print("Using Database: ", os.environ.get("DATABASE_URL"))
init_db()
print("PostgreSQL Neon DB Schema Initialized Successfully!")
