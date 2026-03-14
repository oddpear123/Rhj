import asyncio
import os
from dotenv import load_dotenv
from pathlib import Path

# Load env before importing app.database
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

from app.database import init_db

async def run_init():
    print(f"Initializing database at: {os.getenv('DATABASE_URL')}")
    print(f"TNS_ADMIN: {os.getenv('TNS_ADMIN')}")
    try:
        await init_db()
        print("SUCCESS: Database initialized successfully.")
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")

if __name__ == "__main__":
    asyncio.run(run_init())
