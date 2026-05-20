# app.py

from flask import (
    Flask,
    request,
    render_template_string
)

# Markdown renderer
import markdown

# IMPORTANT:
# Load observability FIRST
import observability

from observability import (
    instrument_flask
)

from agent import Agent


# -------------------------------------------------------------------
# Flask
# -------------------------------------------------------------------

app = Flask(__name__)

instrument_flask(app)


# -------------------------------------------------------------------
# Agent
# -------------------------------------------------------------------

agent = Agent()


# -------------------------------------------------------------------
# Demo Image
# -------------------------------------------------------------------

IMAGE_URL = (
    "https://picsum.photos/900/500"
)


# -------------------------------------------------------------------
# HTML
# -------------------------------------------------------------------

HTML_PAGE = """
<!DOCTYPE html>
<html>

<head>

    <title>
        Your Meetup Advisor Demo App
    </title>

    <style>

        body {
            font-family: Arial, sans-serif;
            background: #f4f4f4;
            margin: 40px;
        }

        .container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            max-width: 1100px;
            margin: auto;
        }

        h1 {
            text-align: center;
        }

        form {
            text-align: center;
            margin-bottom: 20px;
        }

        input[type=text] {
            width: 70%;
            padding: 12px;
            font-size: 16px;
        }

        button {
            padding: 12px 18px;
            font-size: 16px;
            cursor: pointer;
        }

        img {
            width: 100%;
            margin-top: 20px;
            border-radius: 10px;
        }

        .response {
            margin-top: 30px;
            background: #fafafa;
            padding: 25px;
            border-radius: 10px;
            border: 1px solid #ddd;
            overflow-x: auto;
        }

        /* Markdown Styling */

        .response h1,
        .response h2,
        .response h3 {
            margin-top: 24px;
        }

        .response p {
            line-height: 1.6;
        }

        .response code {
            background: #efefef;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: monospace;
        }

        .response pre {
            background: #272822;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
        }

        .response table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 15px;
        }

        .response table,
        .response th,
        .response td {
            border: 1px solid #ccc;
        }

        .response th,
        .response td {
            padding: 10px;
            text-align: left;
        }

        .response blockquote {
            border-left: 4px solid #ccc;
            padding-left: 15px;
            color: #666;
            margin-left: 0;
        }

    </style>

</head>

<body>

<div class="container">

    <h1>
        Your Meetup Advisor
    </h1>

    <h3 style="display: block; text-align: center">
        Built with ❤️ in Python to demonstrate OpenTelemetry integrations for AI and software Observability.
    </h3>

    <form method="POST">

        <input
            type="text"
            name="prompt"
            placeholder="Ask something..."
            required
        >

        <button type="submit">
            Submit
        </button>

    </form>

    <img
        src="{{ image_url }}"
    >

    {% if response_html %}

    <div class="response">

        {{ response_html | safe }}

    </div>

    {% endif %}

</div>

</body>
</html>
"""


# -------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------

@app.route("/", methods=["GET", "POST"])
def home():

    response_html = ""

    if request.method == "POST":

        prompt = request.form.get(
            "prompt"
        )

        response_text = agent.call_llm(
            prompt=prompt,
            session_id="browser-session"
        )

        # -------------------------------------------------------------
        # Convert Markdown -> HTML
        # -------------------------------------------------------------

        response_html = markdown.markdown(
            response_text,

            extensions=[
                "fenced_code",
                "tables",
                "codehilite",
                "toc",
            ]
        )

    return render_template_string(
        HTML_PAGE,
        image_url=IMAGE_URL,
        response_html=response_html
    )


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )