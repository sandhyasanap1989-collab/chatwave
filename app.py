from flask import Flask, render_template, request, redirect

app = Flask(__name__)

messages = []

@app.route("/")
def home():
    return render_template("index.html", messages=messages)

@app.route("/send", methods=["POST"])
def send():
    name = request.form["name"]
    message = request.form["message"]

    if name and message:
        messages.append({
            "name": name,
            "message": message
        })

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)