import requests
from requests.auth import HTTPBasicAuth
import math
from getpass import getpass

BASE_URL = "http://127.0.0.1:8000"
AUTH_MODE = "basic"
access_token: str | None = None
basic_credentials: tuple[str, str] | None = None

def send_request(method, endpoint, item_data=None):
    auth = None
    headers = {}
    if AUTH_MODE == "basic" and basic_credentials is not None:
        username, password = basic_credentials
        auth = HTTPBasicAuth(username, password)
    elif AUTH_MODE == "jwt" and access_token is not None:
        headers["Authorization"] = f"Bearer {access_token}"
    try:
        response = requests.request(method=method, url=f"{BASE_URL}{endpoint}", json=item_data, auth=auth, headers=headers, timeout=10)
        print(f"HTTP Status: {response.status_code}")
        print(response.json())
        return response
    except requests.exceptions.RequestException as error:
        print(f"Connection error: {error}")
        return None

def input_item_data():
    name = input("Enter skin name: ").strip()
    weapon = input("Enter weapon: ").strip()
    exterior = input("Enter exterior: ").strip()
    float_input = input("Enter float value (0-1): ").strip()
    pattern_input = input("Enter pattern (0-999): ").strip()
    stat_trak_input = input("StatTrak (yes/no): ").strip().lower()
    if not all((name, weapon, exterior)):
        print("Name, weapon and exterior cannot be empty")
        return None
    try:
        float_value = float(float_input)
        pattern = int(pattern_input)
    except ValueError:
        print("Float value and pattern must be valid numbers")
        return None
    if not math.isfinite(float_value) or not 0 <= float_value <= 1:
        print("Float value must be between 0 and 1")
        return None
    if not 0 <= pattern <= 999:
        print("Pattern must be between 0 and 999")
        return None
    if stat_trak_input not in ("yes", "no"):
        print("StatTrak must be yes or no")
        return None
    return {"name": name, "weapon": weapon,"exterior": exterior, "float_value": float_value, "pattern": pattern, "stat_trak": stat_trak_input == "yes"}

def register_user():
    username = input("Enter username: ").strip()
    password = getpass("Enter password: ")
    try:
        response = requests.post(f"{BASE_URL}/register", json={"username": username,"password": password}, timeout=10)
        print(f"HTTP Status: {response.status_code}")
        print(response.json())
    except requests.exceptions.RequestException as error:
        print(f"Connection error: {error}")

def login_user():
    global access_token, basic_credentials
    access_token = None
    basic_credentials = None
    username = input("Enter username: ").strip()
    password = getpass("Enter password: ")
    if AUTH_MODE == "basic":
        try:
            response = requests.get(f"{BASE_URL}/items", auth=HTTPBasicAuth(username, password), timeout=10)
            if response.status_code == 200:
                basic_credentials = (username, password)
                print("Basic authentication successful")
            else:
                print(f"Authentication failed: {response.status_code}")
                print(response.json())
        except requests.exceptions.RequestException as error:
            print(f"Connection error: {error}")
    elif AUTH_MODE == "jwt":
        try:
            response = requests.post(f"{BASE_URL}/login",json={ "username": username, "password": password }, timeout=10)
            if response.status_code == 200:
                data = response.json()
                access_token = data["access_token"]
                print("JWT authentication successful")
                print(f"Token expires in: {data['expires_in']} seconds")
            else:
                print(f"Authentication failed: {response.status_code}")
                print(response.json())
        except requests.exceptions.RequestException as error:
            print(f"Connection error: {error}")

def view_inventory():
    send_request("GET", "/items")

def view_item_details():
    item_id = input("Enter item ID: ").strip()
    if not item_id.isdigit() or int(item_id) <= 0:
        print("Item ID must be a positive integer")
        return
    send_request("GET", f"/items/{item_id}")

def create_item():
    print("\n===== ADD NEW SKIN =====")
    item_data = input_item_data()
    if item_data is None:
        return
    send_request("POST", "/items", item_data)

def update_item():
    print("\n===== UPDATE SKIN =====")
    item_id = input("Enter item ID: ").strip()
    if not item_id.isdigit() or int(item_id) <= 0:
        print("Item ID must be a positive integer")
        return
    item_data = input_item_data()
    if item_data is None:
        return
    send_request("PUT", f"/items/{item_id}", item_data)

def delete_item():
    print("\n===== DELETE SKIN =====")
    item_id = input("Enter item ID: ").strip()
    if not item_id.isdigit() or int(item_id) <= 0:
        print("Item ID must be a positive integer")
        return
    confirmation = input(f"Are you sure you want to delete item {item_id}? (yes/no): ").strip().lower()
    if confirmation != "yes":
        print("Deletion cancelled")
        return
    send_request("DELETE", f"/items/{item_id}")

def main_menu():
    while True:
        print("\n＼(＾O＾)／ CS2 INVENTORY CLIENT (╯°□°）╯︵ ┻━┻")
        print("1. Register user")
        print("2. Login")
        print("3. View inventory")
        print("4. View item details")
        print("5. Add new skin")
        print("6. Update skin")
        print("7. Delete skin")
        print("0. Exit")
        choice = input("Select option: ").strip()
        if choice == "1":
            register_user()
        elif choice == "2":
            login_user()
        elif choice == "3":
            view_inventory()
        elif choice == "4":
            view_item_details()
        elif choice == "5":
            create_item()
        elif choice == "6":
            update_item()
        elif choice == "7":
            delete_item()
        elif choice == "0":
            print("Exiting client...")
            break
        else:
            print("Invalid option")

if __name__ == "__main__":
    main_menu()

