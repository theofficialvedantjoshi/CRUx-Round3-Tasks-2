import os
from flask import Flask, jsonify, request
from flask import url_for
from dotenv import load_dotenv
import requests
from authlib.integrations.flask_client import OAuth
import redis
import json
from models.data import Auth
from dataclasses import asdict

load_dotenv()

LICHESS_HOST = os.getenv("LICHESS_HOST", "https://lichess.org")
r = redis.Redis(host="localhost", port=6379, db=0)

app = Flask(__name__)
app.secret_key = os.urandom(24)

oauth = OAuth(app)
oauth.register(
    name="lichess",
    client_id=os.getenv("LICHESS_CLIENT_ID"),
    client_secret=os.getenv("LICHESS_CLIENT_SECRET"),
    authorize_url=f"{LICHESS_HOST}/oauth",
    access_token_url=f"{LICHESS_HOST}/api/token",
    client_kwargs={
        "code_challenge_method": "S256",
        "token_endpoint_auth_method": "client_secret_post",
    },
)

session = {}


@app.route("/login/<discord_user_id>")
def login(discord_user_id):
    session["discord_user_id"] = discord_user_id
    redirect_uri = url_for("authorize", _external=True)
    return oauth.lichess.authorize_redirect(
        redirect_uri,
        scope=" ".join(
            [
                "challenge:read",
                "challenge:write",
                "email:read",
                "tournament:write",
                "board:play",
            ]
        ),
    )


@app.route("/authorize")
def authorize():
    discord_user_id = session.get("discord_user_id", None)
    if discord_user_id is None:
        return jsonify({"error": "discord_user_id is required"}), 400
    try:
        token = oauth.lichess.authorize_access_token()
        bearer = token["access_token"]
        headers = {"Authorization": f"Bearer {bearer}"}
        response = requests.get(f"{LICHESS_HOST}/api/account", headers=headers)
        response.raise_for_status()
        auth = Auth(
            discord_id=discord_user_id,
            token=bearer,
            lichess_username=response.json()["username"],
        )
        r.set(
            f"auth_{discord_user_id}",
            json.dumps(asdict(auth)),
            ex=3600,
        )
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(host="localhost", port=5000)
