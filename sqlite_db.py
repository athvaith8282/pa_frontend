import aiosqlite
from config import SQLITE_FILEPATH

async def get_sqlite_conn():
    conn = await aiosqlite.connect(SQLITE_FILEPATH)
    return conn

async def create_thread_db():
    async with aiosqlite.connect(SQLITE_FILEPATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                thread_id TEXT PRIMARY KEY,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def get_distinct_thread_ids(db_path: str = SQLITE_FILEPATH)->list[str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT DISTINCT thread_id FROM threads") as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def add_thread_to_db(thread_id, title = None, db_path: str = SQLITE_FILEPATH):
    if not title:
        title = f"chat_{thread_id}"
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO threads (thread_id, title) VALUES (?, ?)",
            (thread_id, title)
        )
        await db.commit()
        return thread_id