import sqlite3
import datetime
from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from LB3_Database import init_db, DB_PATH
import os
import jwt
from dotenv import load_dotenv
from typing import Any

app = Flask(__name__)
HOST = "127.0.0.1"
PORT = 8000
load_dotenv()
AUTH_MODE = "basic"
if AUTH_MODE not in ("basic", "jwt"):
    raise ValueError("Unsupported authentication mode")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 1
if not JWT_SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY not set")

@app.route('/', methods=["GET"])
def index():
    return jsonify({"message": "CS2 Inventory API is running!"}), 200

def verify_basic_auth():
    auth = request.authorization
    if not auth or auth.type.lower() != "basic":
        return None
    username = auth.username
    password = auth.password
    if not username or password is None:
        return None
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, username, password_hash
            FROM users
            WHERE username = ?""", (username,))
        user = cursor.fetchone()
    finally:
        connection.close()
    if user is None:
        return None
    if not check_password_hash(user[2], password):
        return None
    return {"id": user[0], "username": user[1]}

def verify_jwt_auth():
    auth = request.authorization
    if not auth or auth.type.lower() != "bearer":
        return None
    token =auth.token
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options={"require": ["sub", "iat", "exp"]})
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError):
        return None
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, username
            FROM users
            WHERE id = ?""", (user_id,))
        user = cursor.fetchone()
    finally:
        connection.close()
    if user is None:
        return None
    return {"id": user[0], "username": user[1]}

def authenticate():
    if AUTH_MODE == "basic":
        return verify_basic_auth()
    if AUTH_MODE == "jwt":
        return verify_jwt_auth()
    return None

def validate_item_data(data: Any) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(data, dict):
        return None, "Invalid JSON data"
    text_fields = ("name", "weapon", "exterior")
    cleaned: dict[str, Any] = {}
    for field in text_fields:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            return None, f"{field} must be a non-empty string"
        cleaned[field] = value.strip()
    float_value = data.get("float_value")
    pattern = data.get("pattern")
    stat_trak = data.get("stat_trak", False)
    if isinstance(float_value, bool) or not isinstance(float_value, (int, float)) or not 0 <= float_value <= 1:
        return None, "Float value must be between 0 and 1"
    if isinstance(pattern, bool) or not isinstance(pattern, int) or not 0 <= pattern <= 999:
        return None, "Pattern must be between 0 and 999"
    if not isinstance(stat_trak, bool):
        return None, "StatTrak must be a boolean"
    cleaned["float_value"] = float_value
    cleaned["pattern"] = pattern
    cleaned["stat_trak"] = int(stat_trak)
    return cleaned, None

def get_validated_item_data():
    data = request.get_json(silent=True)
    return validate_item_data(data)

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON data"}), 400
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not username.strip():
        return jsonify({"error": "Username must be a non-empty string"}), 400
    if not isinstance(password, str) or len(password) < 8:
        return jsonify({"error": "Password must contain at lease 8 characters"}), 400
    username = username.strip()
    password_hash = generate_password_hash(password)
    created_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("""
        INSERT INTO users (username, password_hash, created_at)
        VALUES (?, ?, ?)""", (username, password_hash, created_at))
        user_id = cursor.lastrowid
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        return jsonify({"error": "Username already exists"}), 409
    finally:
        connection.close()
    return jsonify({"status": "success", "message": "User registered successfully", "user_id": user_id, "username": username}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON data"}), 400
    username = data.get("username")
    password = data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "invalid credentials"}), 401
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, username, password_hash
            FROM users
            WHERE username = ?""", (username,))
        user = cursor.fetchone()
    finally:
        connection.close()
    if user is None or not check_password_hash(user[2], password):
        return jsonify({"error": "Invalid credentials"}), 401
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {"sub": str(user[0]), "iat": now, "exp": now + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)}
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return jsonify({"status": "success", "access_token": token, "token_type": "Bearer", "expires_in": JWT_EXPIRATION_HOURS * 3600}), 200

@app.route("/items", methods=["GET"])
@app.route("/inventory", methods=["GET"])
def get_items():
    user= authenticate()
    if user is None:
        return jsonify({"error": "Authentication required or invalid credentials"}), 401
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, name, weapon, exterior
            FROM skins
            WHERE user_id = ?
            ORDER BY id""", (user["id"],))
        rows = cursor.fetchall()
    finally:
        connection.close()
    items = []
    for row in rows:
        items.append({"id": row[0], "name": row[1], "weapon": row[2], "exterior": row[3]})
    return jsonify({"count": len(items), "items": items}), 200

@app.route("/items/<int:item_id>", methods=["GET"])
@app.route("/inventory/<int:item_id>", methods=["GET"])
def get_item(item_id):
    user= authenticate()
    if user is None:
        return jsonify({"error": "Authentication required or invalid credentials"}), 401
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, name, weapon, exterior, float_value, pattern, stat_trak
            FROM skins
            WHERE id = ? AND user_id = ?""", (item_id, user["id"]))
        item = cursor.fetchone()
    finally:
        connection.close()
    if item is None:
        return jsonify({"error": "Item not found"}), 404
    return jsonify ({"id": item[0], "name": item[1], "weapon": item[2], "exterior": item[3], "float_value": item[4], "pattern": item[5], "stat_trak": bool(item[6])}), 200

@app.route("/items", methods=["POST"])
@app.route("/inventory", methods=["POST"])
def create_item():
    user = authenticate()
    if user is None:
        return jsonify({"error": "Authentication required or invalid credentials"}), 401
    values, error = get_validated_item_data()
    if values is None:
        return jsonify({"error": error}), 400
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO skins (user_id, name, weapon, exterior, float_value, pattern, stat_trak)
            VALUES (?, ?, ?, ?, ?, ?, ?)""", (user["id"], values["name"], values["weapon"], values["exterior"], values["float_value"], values["pattern"], values["stat_trak"]))
        item_id = cursor.lastrowid
        connection.commit()
    finally:
        connection.close()
    return jsonify({"status": "success", "message": "item created successfully", "item_id": item_id}), 201

@app.route("/items/<int:item_id>", methods=["PUT"])
@app.route("/inventory/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    user = authenticate()
    if user is None:
        return jsonify({"error": "Authentication required or invalid credentials"}), 401
    values, error = get_validated_item_data()
    if values is None:
        return jsonify({"error": error}), 400
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE skins
            SET name = ?, weapon = ?, exterior = ?, float_value = ?, pattern = ?, stat_trak = ?
            WHERE id = ? AND user_id = ?""", (values["name"], values["weapon"], values["exterior"], values["float_value"], values["pattern"], values["stat_trak"], item_id, user["id"]))
        updated_rows = cursor.rowcount
        connection.commit()
    finally:
        connection.close()
    if updated_rows == 0:
        return jsonify({"error": "item not found"}), 404
    return jsonify({"status": "success", "message": "item updated successfully", "item_id": item_id}), 200

@app.route("/items/<int:item_id>", methods=["DELETE"])
@app.route("/inventory/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    user = authenticate()
    if user is None:
        return jsonify({"error": "Authentication required or invalid credentials"}), 401
    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.execute("""
            DELETE FROM skins
            WHERE id = ? AND user_id = ?""", (item_id, user["id"]))
        deleted_rows = cursor.rowcount
        connection.commit()
    finally:
        connection.close()
    if deleted_rows == 0:
        return jsonify({"error": "Item not found"}), 404
    return jsonify({"status": "success", "message": "Item deleted successfully", "item_id": item_id}), 200

def main():
    init_db()
    app.run(host=HOST, port=PORT)

if __name__ == "__main__":
    main()