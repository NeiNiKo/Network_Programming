import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_PATH = "events.db"
HOST = "127.0.0.1"
PORT = 8000

def init_db():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_id INTEGER NOT NULL,
        source TEXT NOT NULL,
        level TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT NOT NULL,
        record_number INTEGER UNIQUE
    )""")
    connection.commit()
    connection.close()
@app.route("/", methods=["GET"])
def index():
    return "Event Logger Server is running", 200

@app.route("/events", methods=["POST"])
def add_event():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON data"}), 400
    required_fields = ["event_id", "source", "level", "message", "created_at"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    if type(data["event_id"]) is not int:
        return jsonify({"error": "event_id must be an integer"}), 400
    for field in required_fields[1:]:
        if not isinstance(data[field], str) or not data[field].strip():
            return jsonify({"error": f"Field {field} must be a non-empty string"}), 400
    record_number = data.get("record_number")
    if record_number is not None:
        if type(record_number) is not int or record_number < 0:
            return jsonify({"error": "record_number must be a non-negative integer"}), 400
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(""" INSERT INTO events (
        event_id,
        source,
        level,
        message,
        created_at,
        record_number
    ) VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT (record_number) DO NOTHING""",(
        data["event_id"],
        data["source"],
        data["level"],
        data["message"],
        data["created_at"],
        record_number
    ))
    inserted = cursor.rowcount == 1
    event_db_id = cursor.lastrowid if inserted else None
    connection.commit()
    connection.close()
    if not inserted:
        return jsonify({"status": "duplicate", "message": "Event already exists"}), 200
    return jsonify({"status": "success", "message": "Event saved successfully", "id": event_db_id}), 201

@app.route("/events", methods=["GET"])
def get_events():
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("""
        SELECT id, event_id, source, level, message, created_at, record_number
        FROM events
        ORDER BY created_at, id""")
    rows = cursor.fetchall()
    connection.close()
    events = []
    for row in rows:
        events.append({"id": row[0], "event_id": row[1], "source": row[2], "level": row[3], "message": row[4], "created_at": row[5], "record_number": row[6]})
    return jsonify({"count": len(events), "events": events}), 200

def main():
    init_db()
    app.run(host=HOST, port=PORT)

if __name__ == "__main__":
    main()