from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import uuid

app = Flask(__name__)
app.secret_key = "chatwave-secret-key"

USERS_FILE = "users.json"
MESSAGES_FILE = "messages.json"
GROUPS_FILE = "groups.json"


def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_users():
    return load_json(USERS_FILE, {})


def save_users(users):
    save_json(USERS_FILE, users)


def load_messages():
    return load_json(MESSAGES_FILE, [])


def save_messages(messages):
    save_json(MESSAGES_FILE, messages)


def load_groups():
    return load_json(GROUPS_FILE, {})


def save_groups(groups):
    save_json(GROUPS_FILE, groups)


# =========================
# HOME
# =========================

@app.route("/")
def home():

    if "username" not in session:
        return render_template("index.html", logged_in=False)

    username = session["username"]

    users = load_users()
    groups = load_groups()
    messages = load_messages()

    other_users = [
        user for user in users
        if user != username
    ]

    user_groups = []

    for group_id, group in groups.items():

        if username in group.get("members", []):

            user_groups.append({
                "id": group_id,
                "name": group.get("name", ""),
                "creator": group.get("creator", ""),
                "members": group.get("members", [])
            })

    chat_type = session.get("chat_type")
    chat_with = session.get("chat_with")
    group_id = session.get("group_id")

    visible_messages = []

    # PRIVATE CHAT
    if chat_type == "private" and chat_with:

        for msg in messages:

            if msg.get("type") != "private":
                continue

            sender = msg.get("sender")
            receiver = msg.get("receiver")

            if (
                sender == username and receiver == chat_with
            ) or (
                sender == chat_with and receiver == username
            ):
                visible_messages.append(msg)

    # GROUP CHAT
    elif chat_type == "group" and group_id:

        group = groups.get(group_id)

        if group and username in group.get("members", []):

            for msg in messages:

                if (
                    msg.get("type") == "group"
                    and msg.get("group_id") == group_id
                ):
                    visible_messages.append(msg)

    selected_group = groups.get(group_id)

    return render_template(
        "index.html",
        logged_in=True,
        username=username,
        users=other_users,
        groups=user_groups,
        chat_type=chat_type,
        chat_with=chat_with,
        group_id=group_id,
        selected_group=selected_group,
        messages=visible_messages
    )


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["POST"])
def register():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    if not username or not password:
        return "Username and password are required."

    if len(username) < 3:
        return "Username must be at least 3 characters."

    if len(password) < 6:
        return "Password must be at least 6 characters."

    users = load_users()

    if username in users:
        return "Username already exists."

    users[username] = {
        "password": generate_password_hash(password)
    }

    save_users(users)

    session["username"] = username
    session["chat_type"] = None

    session.pop("chat_with", None)
    session.pop("group_id", None)

    return redirect("/")


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["POST"])
def login():

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    users = load_users()

    if username not in users:
        return "Invalid username or password."

    stored_password = users[username].get("password", "")

    if not check_password_hash(stored_password, password):
        return "Invalid username or password."

    session["username"] = username
    session["chat_type"] = None

    session.pop("chat_with", None)
    session.pop("group_id", None)

    return redirect("/")


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# PRIVATE CHAT
# =========================

@app.route("/set-chat", methods=["POST"])
def set_chat():

    if "username" not in session:
        return redirect("/")

    username = session["username"]
    chat_with = request.form.get("chat_with", "").strip()

    users = load_users()

    if chat_with in users and chat_with != username:

        session["chat_type"] = "private"
        session["chat_with"] = chat_with

        session.pop("group_id", None)

    return redirect("/")


# =========================
# EXIT PRIVATE CHAT
# =========================

@app.route("/exit-chat", methods=["POST"])
def exit_chat():

    if "username" not in session:
        return redirect("/")

    session["chat_type"] = None
    session.pop("chat_with", None)
    session.pop("group_id", None)

    return redirect("/")


# =========================
# CREATE GROUP
# =========================

@app.route("/create-group", methods=["POST"])
def create_group():

    if "username" not in session:
        return redirect("/")

    username = session["username"]

    group_name = request.form.get("group_name", "").strip()

    if not group_name:
        return redirect("/")

    groups = load_groups()

    group_id = str(uuid.uuid4())

    groups[group_id] = {
        "name": group_name,
        "creator": username,
        "members": [username]
    }

    save_groups(groups)

    session["chat_type"] = "group"
    session["group_id"] = group_id

    session.pop("chat_with", None)

    return redirect("/")


# =========================
# SELECT GROUP
# =========================

@app.route("/set-group", methods=["POST"])
def set_group():

    if "username" not in session:
        return redirect("/")

    username = session["username"]
    group_id = request.form.get("group_id", "")

    groups = load_groups()

    group = groups.get(group_id)

    if not group:
        return redirect("/")

    if username not in group.get("members", []):
        return redirect("/")

    session["chat_type"] = "group"
    session["group_id"] = group_id

    session.pop("chat_with", None)

    return redirect("/")


# =========================
# ADD MULTIPLE MEMBERS
# =========================

@app.route("/add-member", methods=["POST"])
def add_member():

    if "username" not in session:
        return redirect("/")

    username = session["username"]

    group_id = request.form.get("group_id", "").strip()

    # Get multiple selected users
    new_members = request.form.getlist("members")

    groups = load_groups()
    users = load_users()

    group = groups.get(group_id)

    if not group:
        return redirect("/")

    # Only creator can add members
    if group.get("creator") != username:
        return redirect("/")

    # Add every selected member
    for new_member in new_members:

        new_member = new_member.strip()

        if new_member in users and new_member not in group["members"]:
            group["members"].append(new_member)

    save_groups(groups)

    return redirect("/")


# =========================
# EXIT GROUP
# =========================

@app.route("/exit-group", methods=["POST"])
def exit_group():

    if "username" not in session:
        return redirect("/")

    username = session["username"]
    group_id = session.get("group_id")

    groups = load_groups()

    group = groups.get(group_id)

    if not group:
        session["chat_type"] = None
        session.pop("group_id", None)
        return redirect("/")

    # Remove current user
    if username in group.get("members", []):
        group["members"].remove(username)

    # If creator exits, delete the group
    if group.get("creator") == username:

        # Remove group messages
        messages = load_messages()

        messages = [
            msg for msg in messages
            if not (
                msg.get("type") == "group"
                and msg.get("group_id") == group_id
            )
        ]

        save_messages(messages)

        del groups[group_id]

    else:

        save_groups(groups)

    session["chat_type"] = None
    session.pop("group_id", None)
    session.pop("chat_with", None)

    return redirect("/")


# =========================
# SEND MESSAGE
# =========================

@app.route("/send", methods=["POST"])
def send():

    if "username" not in session:
        return redirect("/")

    sender = session["username"]
    message = request.form.get("message", "").strip()

    if not message:
        return redirect("/")

    messages = load_messages()

    chat_type = session.get("chat_type")

    # PRIVATE
    if chat_type == "private":

        receiver = session.get("chat_with")

        if not receiver:
            return redirect("/")

        users = load_users()

        if receiver not in users:
            return redirect("/")

        messages.append({
            "id": str(uuid.uuid4()),
            "type": "private",
            "sender": sender,
            "receiver": receiver,
            "message": message
        })

    # GROUP
    elif chat_type == "group":

        group_id = session.get("group_id")

        groups = load_groups()
        group = groups.get(group_id)

        if not group:
            return redirect("/")

        if sender not in group.get("members", []):
            return redirect("/")

        messages.append({
            "id": str(uuid.uuid4()),
            "type": "group",
            "group_id": group_id,
            "sender": sender,
            "message": message
        })

    else:
        return redirect("/")

    save_messages(messages)

    return redirect("/")


# =========================
# GET MESSAGES
# =========================

@app.route("/messages")
def get_messages():

    if "username" not in session:
        return jsonify([])

    username = session["username"]
    chat_type = session.get("chat_type")

    messages = load_messages()

    result = []

    # PRIVATE
    if chat_type == "private":

        chat_with = session.get("chat_with")

        if not chat_with:
            return jsonify([])

        for msg in messages:

            if msg.get("type") != "private":
                continue

            sender = msg.get("sender")
            receiver = msg.get("receiver")

            if (
                sender == username and receiver == chat_with
            ) or (
                sender == chat_with and receiver == username
            ):
                result.append(msg)

    # GROUP
    elif chat_type == "group":

        group_id = session.get("group_id")

        groups = load_groups()
        group = groups.get(group_id)

        if not group:
            return jsonify([])

        if username not in group.get("members", []):
            return jsonify([])

        for msg in messages:

            if (
                msg.get("type") == "group"
                and msg.get("group_id") == group_id
            ):
                result.append(msg)

    return jsonify(result)


# =========================
# CLEAR CHAT
# =========================

@app.route("/clear-chat", methods=["POST"])
def clear_chat():

    if "username" not in session:
        return redirect("/")

    username = session["username"]
    chat_type = session.get("chat_type")

    messages = load_messages()

    # PRIVATE CHAT
    if chat_type == "private":

        chat_with = session.get("chat_with")

        if not chat_with:
            return redirect("/")

        new_messages = []

        for msg in messages:

            if msg.get("type") != "private":

                new_messages.append(msg)

                continue

            sender = msg.get("sender")
            receiver = msg.get("receiver")

            this_chat = (
                sender == username and receiver == chat_with
            ) or (
                sender == chat_with and receiver == username
            )

            if not this_chat:
                new_messages.append(msg)

        save_messages(new_messages)

    # GROUP CHAT
    elif chat_type == "group":

        group_id = session.get("group_id")

        groups = load_groups()
        group = groups.get(group_id)

        if not group:
            return redirect("/")

        # Only creator can clear
        if group.get("creator") != username:
            return redirect("/")

        new_messages = []

        for msg in messages:

            if not (
                msg.get("type") == "group"
                and msg.get("group_id") == group_id
            ):
                new_messages.append(msg)

        save_messages(new_messages)

    return redirect("/")


# =========================
# RUN
# =========================

if __name__ == "__main__":
    app.run(debug=True)