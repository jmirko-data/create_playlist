from flask import Flask, redirect, request, session
import requests
import os
import urllib.parse
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("SPOTIFY_REDIRECT_URI")
TOKEN_URL = os.environ.get("TOKEN_URL")
AUTH_URL = os.environ.get("AUTH_URL")
API_BASE_URL = os.environ.get("API_BASE_URL")

@app.route('/')
def index():
    return redirect('/login')

@app.route("/login")
def login():
    tg_id = request.args.get("tg_id")
    session["tg_id"] = tg_id
    
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "playlist-modify-private playlist-modify-public",
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)

@app.route("/callback")
def callback():
    if 'error' in request.args:
        return jsonify({"error": request.args['error']})
    
    if 'code' in request.args:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET

        }
  
        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()
        session['access_token']= token_info['access_token']
        session['refresh_token']= token_info['refresh_token']
        session['expires_at']= datetime.now().timestamp() + token_info['expires_in']

        return redirect('/playlists')

@app.route('/playlists')
def create_playlists():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')
    
    headers = {
        'Authorization':f"Bearer {session['access_token']}",
        "Content-Type": "application/json"
    }

    data = {
    "name": "Mood_playlist2",
    "description": "this is your moodplalist",
    "public": False
    }

    response = requests.post(API_BASE_URL + 'me/playlists', headers=headers, json=data)
    playlists = response.json()
    session['playlist_id'] = playlists['id']

    return redirect('/songs')


@app.route('/songs')
def add_songs():
    if 'access_token' not in session:
        return redirect('/login')
    
    if datetime.now().timestamp() > session['expires_at']:
        return redirect('/refresh-token')
    
    if 'playlist_id' not in session:
        return "Playlist ID not found. Crea prima la playlist.", 400
    
    headers = {
        'Authorization':f"Bearer {session['access_token']}",
        "Content-Type": "application/json"
    }

    data = {
        "uris": [
        "spotify:track:7InzmgtRkwsheHlrUz0VLK"
    ],
    "position": 0
    }

    playlist_id = session['playlist_id']
    response = requests.post(f"{API_BASE_URL}playlists/{playlist_id}/tracks", headers=headers, json=data)
    songs = response.json()
    return jsonify(songs)

@app.route("/debug")
def debug():
    return {
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET,
        "REDIRECT_URI": REDIRECT_URI,
        "AUTH_URL": AUTH_URL,
        "TOKEN_URL": TOKEN_URL
    }

