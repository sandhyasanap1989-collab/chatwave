from flask import Flask, render_template, request, redirect, session
import json
import os

app = Flask(__name__)
app.secret_key = "chatwave-secret-key"

MESSAGES_FILE = "messages.json"


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


@app.route("/")
def home():
    messages = load_messages()
    return render_template("index.html", messages=messages)


@app.route("/set-name", methods=["POST"])
def set_name():
    name = request.form.get("name", "").strip()

    if name:
        session["name"] = name

    return redirect("/")


@app.route("/send", methods=["POST"])
def send():
    name = session.get("name")

    message = request.form.get("message", "").strip()

    if name and message:
        messages = load_messages()

        messages.append({
            "name": name,
            "message": message
        })

        save_messages(messages)

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)