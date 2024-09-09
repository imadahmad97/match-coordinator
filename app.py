from flask import Flask, request, redirect, url_for, session, jsonify, render_template
import boto3
import logging

app = Flask(__name__)
app.config.from_object("config.Config")

cognito = boto3.client("cognito-idp", region_name=app.config["COGNITO_REGION"])


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
            # Store the session and username to complete the challenge later
            session["cognito_session"] = response["Session"]
            session["username"] = username
            # Render a form to ask the user for a new password
            return render_template("new_password_required.html")

        # If authentication is successful, process the IdToken
        if "AuthenticationResult" in response:
            access_token = response["AuthenticationResult"]["IdToken"]
            return render_template("post_login.html", token=access_token)
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
            return render_template("post_login.html", token=access_token)
        else:
            return jsonify({"error": "Failed to complete new password challenge."}), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500
