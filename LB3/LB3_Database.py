import sqlite3

DB_PATH = "inventory.db"

def init_db():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at     TEXT NOT NULL
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS skins(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        weapon TEXT NOT NULL,
        exterior TEXT NOT NULL,
        float_value REAL NOT NULL CHECK(float_value BETWEEN 0 AND 1),
        pattern INTEGER NOT NULL CHECK(pattern BETWEEN 0 and 999),
        stat_trak INTEGER NOT NULL DEFAULT 0 CHECK(stat_trak IN (0, 1)),
        FOREIGN KEY (user_id) REFERENCES users(id)        
    )""")
    connection.commit()
    connection.close()

if  __name__ == "__main__":
    init_db()
    print("Database created")