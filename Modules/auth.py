import base64
import json
import os
import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from config import CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, SCOPES


TOKEN_FILE = "token.json"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    auth_code = None

    def do_GET(self):
        query = urlparse(self.path).query
        params = parse_qs(query)

        OAuthCallbackHandler.auth_code = params.get("code", [None])[0]

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Authentication successful. You may close this window.")


def save_token(token_data):
    with open(TOKEN_FILE, "w") as file:
        json.dump(token_data, file, indent=4)


def load_token():
    if not os.path.exists(TOKEN_FILE):
        return None

    with open(TOKEN_FILE, "r") as file:
        return json.load(file)


def get_basic_auth_header():
    raw = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded = base64.b64encode(raw.encode()).decode()

    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded"
    }


def get_new_token():
    auth_url = (
        "https://developer.api.autodesk.com/authentication/v2/authorize"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={SCOPES}"
    )

    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8080), OAuthCallbackHandler)
    server.handle_request()

    code = OAuthCallbackHandler.auth_code

    if not code:
        raise Exception("No authorization code received.")

    token_url = "https://developer.api.autodesk.com/authentication/v2/token"

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post(
        token_url,
        headers=get_basic_auth_header(),
        data=data
    )

    if response.status_code != 200:
        raise Exception(f"Token error {response.status_code}: {response.text}")

    token_data = response.json()
    save_token(token_data)

    return token_data["access_token"]


def refresh_token(refresh_token_value):
    token_url = "https://developer.api.autodesk.com/authentication/v2/token"

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value
    }

    response = requests.post(
        token_url,
        headers=get_basic_auth_header(),
        data=data
    )

    if response.status_code != 200:
        return get_new_token()

    token_data = response.json()
    save_token(token_data)

    return token_data["access_token"]


def get_access_token():
    token_data = load_token()

    if token_data and "refresh_token" in token_data:
        return refresh_token(token_data["refresh_token"])

    return get_new_token()