# auth_helpers.py
import os
import json
import bcrypt
from email_validator import validate_email, EmailNotValidError

USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode(), bcrypt.gensalt()).decode()

def check_password(plain_password: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed.encode())

def email_is_valid(email: str) -> bool:
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False

def find_user_by_email(email: str):
    users = load_users()
    for u in users:
        if u.get("email") == email:
            return u
    return None

def create_user(name: str, email: str, password: str):
    if not email_is_valid(email):
        raise ValueError("Invalid email")
    users = load_users()
    if find_user_by_email(email):
        raise ValueError("User already exists")
    user = {
        "name": name,
        "email": email,
        "password": hash_password(password)
    }
    users.append(user)
    save_users(users)
    return user