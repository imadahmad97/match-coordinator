from flask import (
    Flask,
    request,
    redirect,
    url_for,
    session,
    jsonify,
    render_template,
    flash,
)
from functools import wraps
import boto3
import logging

app = Flask(__name__)
app.config.from_object("config.Config")

cognito = boto3.client("cognito-idp", region_name=app.config["COGNITO_REGION"])

# Ensure a secret key for Flask sessions
app.secret_key = app.config["SECRET_KEY"]


# Custom decorator to check if user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "access_token" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
def index():
    # Render the index.html template (your login form)
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    try:
        response = cognito.initiate_auth(
            ClientId=app.config["COGNITO_APP_CLIENT_ID"],
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={
                "USERNAME": username,
                "PASSWORD": password,
            },
        )

        # Log the full response for debugging
        print(f"Cognito response: {response}")

        # Check if 'NEW_PASSWORD_REQUIRED' challenge is present
        if response.get("ChallengeName") == "NEW_PASSWORD_REQUIRED":
            session["cognito_session"] = response["Session"]
            session["username"] = username
            # Render a form to ask the user for a new password
            return render_template("new_password_required.html")

        # If authentication is successful, process the IdToken
        if "AuthenticationResult" in response:
            access_token = response["AuthenticationResult"]["IdToken"]
            # Store the access token in session to indicate a logged-in user
            session["access_token"] = access_token
            return render_template("home.html", token=access_token)
        else:
            return jsonify({"error": "Login failed. No authentication result."}), 401

    except cognito.exceptions.NotAuthorizedException:
        return jsonify({"error": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/complete_new_password", methods=["POST"])
def complete_new_password():
    new_password = request.form.get("new_password")
    name = request.form.get("name")  # Get the name from the form

    try:
        # Use the session token to complete the NEW_PASSWORD_REQUIRED challenge
        response = cognito.respond_to_auth_challenge(
            ClientId=app.config["COGNITO_APP_CLIENT_ID"],
            ChallengeName="NEW_PASSWORD_REQUIRED",
            Session=session.get("cognito_session"),
            ChallengeResponses={
                "USERNAME": session.get("username"),
                "NEW_PASSWORD": new_password,
                "userAttributes.name": name,  # Provide the missing name attribute
            },
        )

        # Check if the challenge was completed and authentication succeeded
        if "AuthenticationResult" in response:
            access_token = response["AuthenticationResult"]["IdToken"]
            session["access_token"] = access_token
            return render_template("home.html", token=access_token)
        else:
            return jsonify({"error": "Failed to complete new password challenge."}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Apply the login_required decorator to all routes except index
@app.route("/clients")
@login_required
def clients():
    return render_template("clients.html")


@app.route("/match_creation_tool")
@login_required
def match_creation_tool():
    return render_template("match_creation_tool.html")


@app.route("/home")
@login_required
def home():
    return render_template("home.html")


@app.route("/logout")
def logout():
    session.clear()  # Clear the session data on logout
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))
