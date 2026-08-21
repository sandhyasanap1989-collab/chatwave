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


# ============================================================
# JSON FUNCTIONS
# ============================================================

def load_json(filename, default):

    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return default


def save_json(filename, data):

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2
        )


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


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    # --------------------------------------------------------
    # NOT LOGGED IN
    # --------------------------------------------------------

    if "username" not in session:

        return render_template(
            "index.html",
            logged_in=False
        )


    # --------------------------------------------------------
    # LOGGED IN
    # --------------------------------------------------------

    username = session["username"]

    users = load_users()
    groups = load_groups()
    messages = load_messages()


    # --------------------------------------------------------
    # OTHER USERS
    # --------------------------------------------------------

    other_users = [
        user
        for user in users
        if user != username
    ]


    # --------------------------------------------------------
    # USER GROUPS
    # --------------------------------------------------------

    user_groups = []

    for group_id, group in groups.items():

        members = group.get("members", [])

        if username in members:

            user_groups.append({
                "id": group_id,
                "name": group.get("name", ""),
                "creator": group.get("creator", ""),
                "members": members
            })


    # --------------------------------------------------------
    # CURRENT CHAT
    # --------------------------------------------------------

    chat_type = session.get("chat_type")
    chat_with = session.get("chat_with")
    group_id = session.get("group_id")

    visible_messages = []


    # ========================================================
    # PRIVATE CHAT
    # ========================================================

    if chat_type == "private" and chat_with:

        for msg in messages:

            if msg.get("type") != "private":
                continue

            sender = msg.get("sender")
            receiver = msg.get("receiver")

            if (
                sender == username
                and receiver == chat_with
            ) or (
                sender == chat_with
                and receiver == username
            ):

                visible_messages.append(msg)


    # ========================================================
    # GROUP CHAT
    # ========================================================

    elif chat_type == "group" and group_id:

        group = groups.get(group_id)

        if group:

            members = group.get("members", [])

            if username in members:

                for msg in messages:

                    if (
                        msg.get("type") == "group"
                        and str(msg.get("group_id"))
                        == str(group_id)
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


# ============================================================
# REGISTER PAGE
# ============================================================

@app.route("/register-page")
def register_page():

    if "username" in session:
        return redirect("/")

    return render_template(
        "register.html"
    )


# ============================================================
# REGISTER
# ============================================================

@app.route("/register", methods=["POST"])
def register():

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )


    # Empty
    if not username or not password:

        return """
        <h2>Username and password are required.</h2>
        <a href="/register-page">Go Back</a>
        """


    # Username length
    if len(username) < 3:

        return """
        <h2>Username must be at least 3 characters.</h2>
        <a href="/register-page">Go Back</a>
        """


    # Password length
    if len(password) < 6:

        return """
        <h2>Password must be at least 6 characters.</h2>
        <a href="/register-page">Go Back</a>
        """


    users = load_users()


    # Existing user
    if username in users:

        return """
        <h2>Username already exists.</h2>
        <a href="/register-page">Try Again</a>
        """


    # Create user
    users[username] = {
        "password": generate_password_hash(password)
    }


    save_users(users)


    # Automatically login
    session.clear()

    session["username"] = username
    session["chat_type"] = None


    return redirect("/")


# ============================================================
# LOGIN
# ============================================================

@app.route("/login", methods=["POST"])
def login():

    username = request.form.get(
        "username",
        ""
    ).strip()

    password = request.form.get(
        "password",
        ""
    )


    users = load_users()


    if username not in users:

        return """
        <h2>Invalid username or password.</h2>
        <a href="/">Try Again</a>
        """


    stored_password = users[username].get(
        "password",
        ""
    )


    try:

        valid_password = check_password_hash(
            stored_password,
            password
        )

    except Exception:

        valid_password = False


    if not valid_password:

        return """
        <h2>Invalid username or password.</h2>
        <a href="/">Try Again</a>
        """


    session.clear()

    session["username"] = username
    session["chat_type"] = None


    return redirect("/")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ============================================================
# PRIVATE CHAT
# ============================================================

@app.route("/set-chat", methods=["POST"])
def set_chat():

    if "username" not in session:
        return redirect("/")


    username = session["username"]

    chat_with = request.form.get(
        "chat_with",
        ""
    ).strip()


    users = load_users()


    if chat_with not in users:
        return redirect("/")


    if chat_with == username:
        return redirect("/")


    session["chat_type"] = "private"
    session["chat_with"] = chat_with

    session.pop(
        "group_id",
        None
    )


    return redirect("/")


# ============================================================
# CLOSE PRIVATE CHAT
# ============================================================

@app.route("/exit-chat", methods=["POST"])
def exit_chat():

    if "username" not in session:
        return redirect("/")


    session["chat_type"] = None

    session.pop(
        "chat_with",
        None
    )


    return redirect("/")


# ============================================================
# CREATE GROUP
# ============================================================

@app.route("/create-group", methods=["POST"])
def create_group():

    if "username" not in session:
        return redirect("/")


    username = session["username"]


    group_name = request.form.get(
        "group_name",
        ""
    ).strip()


    if not group_name:
        return redirect("/")


    groups = load_groups()


    group_id = str(
        uuid.uuid4()
    )


    groups[group_id] = {

        "name": group_name,

        "creator": username,

        "members": [
            username
        ]

    }


    save_groups(groups)


    session["chat_type"] = "group"

    session["group_id"] = group_id

    session.pop(
        "chat_with",
        None
    )


    return redirect("/")


# ============================================================
# SELECT GROUP
# ============================================================

@app.route("/set-group", methods=["POST"])
def set_group():

    if "username" not in session:
        return redirect("/")


    username = session["username"]


    group_id = request.form.get(
        "group_id",
        ""
    )


    groups = load_groups()

    group = groups.get(group_id)


    if not group:
        return redirect("/")


    if username not in group.get(
        "members",
        []
    ):

        return redirect("/")


    session["chat_type"] = "group"

    session["group_id"] = group_id

    session.pop(
        "chat_with",
        None
    )


    return redirect("/")


# ============================================================
# ADD MULTIPLE MEMBERS
# ============================================================

@app.route("/add-member", methods=["POST"])
def add_member():

    if "username" not in session:
        return redirect("/")


    username = session["username"]


    group_id = request.form.get(
        "group_id",
        ""
    )


    members = request.form.getlist(
        "members"
    )


    # Support old single member field too
    old_member = request.form.get(
        "member",
        ""
    ).strip()


    if old_member:

        members.append(
            old_member
        )


    groups = load_groups()
    users = load_users()


    group = groups.get(group_id)


    if not group:
        return redirect("/")


    # Only creator can add members
    if group.get("creator") != username:

        return redirect("/")


    for new_member in members:

        new_member = new_member.strip()


        if not new_member:
            continue


        if new_member not in users:
            continue


        if new_member not in group.get(
            "members",
            []
        ):

            group["members"].append(
                new_member
            )


    save_groups(groups)


    session["chat_type"] = "group"

    session["group_id"] = group_id


    return redirect("/")


# ============================================================
# EXIT GROUP
# ============================================================

@app.route("/exit-group", methods=["POST"])
def exit_group():

    if "username" not in session:
        return redirect("/")


    username = session["username"]

    group_id = session.get(
        "group_id"
    )


    if not group_id:
        return redirect("/")


    groups = load_groups()

    group = groups.get(group_id)


    if not group:

        session["chat_type"] = None

        session.pop(
            "group_id",
            None
        )

        return redirect("/")


    # --------------------------------------------------------
    # HOST
    # --------------------------------------------------------

    if group.get("creator") == username:

        # Delete group
        del groups[group_id]

        save_groups(groups)


        # Delete group messages
        messages = load_messages()


        messages = [

            msg

            for msg in messages

            if not (
                msg.get("type") == "group"
                and str(
                    msg.get("group_id")
                ) == str(group_id)
            )

        ]


        save_messages(messages)


    # --------------------------------------------------------
    # NORMAL MEMBER
    # --------------------------------------------------------

    else:

        members = group.get(
            "members",
            []
        )


        if username in members:

            members.remove(
                username
            )


        group["members"] = members

        save_groups(groups)


    session["chat_type"] = None

    session.pop(
        "group_id",
        None
    )


    return redirect("/")


# ============================================================
# SEND MESSAGE
# ============================================================

@app.route("/send", methods=["POST"])
def send():

    if "username" not in session:
        return redirect("/")


    sender = session["username"]


    message = request.form.get(
        "message",
        ""
    ).strip()


    if not message:
        return redirect("/")


    messages = load_messages()

    chat_type = session.get(
        "chat_type"
    )


    # ========================================================
    # PRIVATE MESSAGE
    # ========================================================

    if chat_type == "private":

        receiver = session.get(
            "chat_with"
        )


        if not receiver:
            return redirect("/")


        users = load_users()


        if receiver not in users:
            return redirect("/")


        messages.append({

            "id": str(
                uuid.uuid4()
            ),

            "type": "private",

            "sender": sender,

            "receiver": receiver,

            "message": message

        })


    # ========================================================
    # GROUP MESSAGE
    # ========================================================

    elif chat_type == "group":

        group_id = session.get(
            "group_id"
        )


        if not group_id:
            return redirect("/")


        groups = load_groups()

        group = groups.get(
            group_id
        )


        if not group:
            return redirect("/")


        # IMPORTANT:
        # Every group member can send
        if sender not in group.get(
            "members",
            []
        ):

            return redirect("/")


        messages.append({

            "id": str(
                uuid.uuid4()
            ),

            "type": "group",

            "group_id": group_id,

            "sender": sender,

            "message": message

        })


    else:

        return redirect("/")


    save_messages(messages)


    return redirect("/")


# ============================================================
# GET MESSAGES
# ============================================================

@app.route("/messages")
def get_messages():

    if "username" not in session:
        return jsonify([])


    username = session["username"]

    chat_type = session.get(
        "chat_type"
    )


    messages = load_messages()

    result = []


    # ========================================================
    # PRIVATE
    # ========================================================

    if chat_type == "private":

        chat_with = session.get(
            "chat_with"
        )


        if not chat_with:
            return jsonify([])


        for msg in messages:

            if msg.get(
                "type"
            ) != "private":

                continue


            sender = msg.get(
                "sender"
            )

            receiver = msg.get(
                "receiver"
            )


            if (

                sender == username
                and receiver == chat_with

            ) or (

                sender == chat_with
                and receiver == username

            ):

                result.append(msg)


    # ========================================================
    # GROUP
    # ========================================================

    elif chat_type == "group":

        group_id = session.get(
            "group_id"
        )


        if not group_id:
            return jsonify([])


        groups = load_groups()

        group = groups.get(
            group_id
        )


        if not group:
            return jsonify([])


        # User must be a member
        if username not in group.get(
            "members",
            []
        ):

            return jsonify([])


        for msg in messages:

            if msg.get(
                "type"
            ) != "group":

                continue


            if str(
                msg.get("group_id")
            ) == str(group_id):

                result.append(msg)


    return jsonify(result)


# ============================================================
# CLEAR CHAT
# ============================================================

@app.route("/clear-chat", methods=["POST"])
def clear_chat():

    if "username" not in session:
        return redirect("/")


    username = session["username"]

    chat_type = session.get(
        "chat_type"
    )


    messages = load_messages()


    # ========================================================
    # PRIVATE CHAT
    # ========================================================

    if chat_type == "private":

        chat_with = session.get(
            "chat_with"
        )


        if not chat_with:
            return redirect("/")


        new_messages = []


        for msg in messages:

            if msg.get(
                "type"
            ) != "private":

                new_messages.append(msg)

                continue


            sender = msg.get(
                "sender"
            )

            receiver = msg.get(
                "receiver"
            )


            current_chat = (

                sender == username
                and receiver == chat_with

            ) or (

                sender == chat_with
                and receiver == username

            )


            if not current_chat:

                new_messages.append(msg)


        save_messages(
            new_messages
        )


    # ========================================================
    # GROUP CHAT
    # ========================================================

    elif chat_type == "group":

        group_id = session.get(
            "group_id"
        )


        groups = load_groups()

        group = groups.get(
            group_id
        )


        if not group:
            return redirect("/")


        # Only host can clear
        if group.get(
            "creator"
        ) != username:

            return redirect("/")


        new_messages = []


        for msg in messages:

            if not (

                msg.get(
                    "type"
                ) == "group"

                and

                str(
                    msg.get("group_id")
                ) == str(group_id)

            ):

                new_messages.append(msg)


        save_messages(
            new_messages
        )


    return redirect("/")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )
    