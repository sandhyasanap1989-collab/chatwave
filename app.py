from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "my_secret_key"


@app.route("/")
def home():
    name = session.get("name")
    messages = session.get("messages", [])
    return render_template("index.html", name=name, messages=messages)


@app.route("/set-name", methods=["POST"])
def set_name():
    name = request.form.get("name")

    if name:
        session["name"] = name

    return redirect("/")


@app.route("/send", methods=["POST"])
def send():
    message = request.form.get("message")

    if message:
        messages = session.get("messages", [])
        messages.append({
            "name": session.get("name", "User"),
            "message": message
        })
        session["messages"] = messages

    return redirect("/")


@app.route("/clear")
def clear():
    session.pop("messages", None)
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)