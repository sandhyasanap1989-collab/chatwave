from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

app = Flask(__name__)
app.secret_key = "chatwave-secret-key"

USERS_FILE = "users.json"
MESSAGES_FILE = "messages.json"


# ==========================================
# USERS
# ==========================================

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return {}


def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=2)


# ==========================================
# MESSAGES
# ==========================================

def load_messages():
    if not os.path.exists(MESSAGES_FILE):
        return []

    try:
        with open(MESSAGES_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return []


def save_messages(messages):
    with open(MESSAGES_FILE, "w", encoding="utf-8") as file:
        json.dump(messages, file, ensure_ascii=False, indent=2)


# ==========================================
# HOME
# ==========================================

@app.route("/")
def home():

    if "username" not in session:
        return render_template(
            "index.html",
            logged_in=False
        )

    username = session["username"]
    chat_with = session.get("chat_with")

    users = load_users()

    # Don't show yourself in the user list
    other_users = [
        user for user in users
        if user != username
    ]

    messages = load_messages()

    private_messages = []

    if chat_with:

        for msg in messages:

            sender = msg.get("sender")
            receiver = msg.get("receiver")

            if (
                sender == username and receiver == chat_with
            ) or (
                sender == chat_with and receiver == username
            ):
                private_messages.append(msg)

    return render_template(
        "index.html",
        logged_in=True,
        username=username,
        users=other_users,
        chat_with=chat_with,
        messages=private_messages
    )


# ==========================================
# REGISTER
# ==========================================

@app.route("/register", methods=["POST"])
def register():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    # Basic validation
    if not username or not password:
        return "Username and password are required."

    if len(username) < 3:
        return "Username must be at least 3 characters."

    if len(password) < 6:
        return "Password must be at least 6 characters."

    users = load_users()

    # Username already exists
    if username in users:
        return "Username already exists. Please choose another."

    # Store HASHED password
    users[username] = {
        "password": generate_password_hash(password)
    }

    save_users(users)

    # Automatically log in after registration
    session["username"] = username

    return redirect("/")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["POST"])
def login():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    users = load_users()

    # User doesn't exist
    if username not in users:
        return "Invalid username or password."

    stored_password = users[username]["password"]

    # Check password
    if not check_password_hash(stored_password, password):
        return "Invalid username or password."

    session["username"] = username
    session.pop("chat_with", None)

    return redirect("/")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ==========================================
# SELECT CHAT USER
# ==========================================

@app.route("/set-chat", methods=["POST"])
def set_chat():

    if "username" not in session:
        return redirect("/")

    username = session["username"]
    chat_with = request.form.get("chat_with", "").strip()

    users = load_users()

    # Make sure selected user actually exists
    if chat_with and chat_with in users and chat_with != username:
        session["chat_with"] = chat_with

    return redirect("/")


# ==========================================
# SEND MESSAGE
# ==========================================

@app.route("/send", methods=["POST"])
def send():

    if "username" not in session:
        return redirect("/")

    sender = session["username"]
    receiver = session.get("chat_with")
    message = request.form.get("message", "").strip()

    if not receiver:
        return redirect("/")

    if not message:
        return redirect("/")

    users = load_users()

    # Receiver must be a real user
    if receiver not in users:
        return redirect("/")

    messages = load_messages()

    messages.append({
        "sender": sender,
        "receiver": receiver,
        "message": message
    })

    save_messages(messages)

    return redirect("/")


# ==========================================
# GET PRIVATE MESSAGES
# ==========================================

@app.route("/messages")
def get_messages():

    if "username" not in session:
        return jsonify([])

    username = session["username"]
    chat_with = session.get("chat_with")

    if not chat_with:
        return jsonify([])

    messages = load_messages()

    private_messages = []

    for msg in messages:

        sender = msg.get("sender")
        receiver = msg.get("receiver")

        # ONLY this conversation
        if (
            sender == username and receiver == chat_with
        ) or (
            sender == chat_with and receiver == username
        ):
            private_messages.append({
                "sender": sender,
                "receiver": receiver,
                "message": msg.get("message", "")
            })

    return jsonify(private_messages)


# ==========================================
# RUN APP
# ==========================================

if __name__ == "__main__":
    app.run(debug=True)