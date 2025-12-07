from flask import Flask, redirect, request, jsonify, session
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

USER_SESSIONS = {}

@app.route('/')
def index():
    return redirect('/login')

@app.route("/login")
def login():
    tg_id = request.args.get("tg_id")
    tracks = request.args.get("songs")  # stringa tipo "7InzmgtRkwsheHlrUz0VLK,4uLU6hMCjMI75M1A2tKUQC"
    tracks_list = tracks.split(",")  # ora è una lista Python
    token = request.args.get("token")

    USER_SESSIONS[token] = {
    "tg_id": tg_id,
    "tracks": tracks_list
    }
    
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": "playlist-modify-private playlist-modify-public",
        "state" : token
    }
    auth_url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    state_token = request.args.get("state") 
    error = request.args.get("error")
    
    if error:
        return jsonify({"error": error})
    
    if code:
        req_body = {
            'code': request.args['code'],
            'grant_type': 'authorization_code',
            'redirect_uri': REDIRECT_URI,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET

        }
  
        response = requests.post(TOKEN_URL, data=req_body)
        token_info = response.json()
        USER_SESSIONS[state_token]["access_token"] = token_info['access_token']
        USER_SESSIONS[state_token]["refresh_token"] = token_info['refresh_token']
        USER_SESSIONS[state_token]["expires_at"] = datetime.now().timestamp() + token_info['expires_in']

        return redirect(f"/playlists?token={state_token}")
    else:
        return "Token non valido o codice mancante", 400
 
@app.route('/playlists')
def create_playlists():
    token = request.args.get("token")
    if not token:
        return redirect('/login')

    user_data = USER_SESSIONS[token]
    
    if datetime.now().timestamp() > user_data["expires_at"]:
        return redirect('/login')
    
    headers = {
        'Authorization':f"Bearer {user_data['access_token']}",
        "Content-Type": "application/json"
    }

    data = {
    "name": "Moody Playlist",
    "description": "Your ultimate playlist 🎶, handpicked by Mir, Deb & Vit 👋. Press play ▶️ and have a blast! 🎉",
    "public": False
    }

    response = requests.post(API_BASE_URL + 'me/playlists', headers=headers, json=data)
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
    
    try:
        playlists = response.json()
    except Exception as e:
        return f"Errore Spotify: {response.status_code} - {response.text}", 400
    
    USER_SESSIONS[token]["playlist_id"] = playlists['id']
    return redirect(f"/songs?token={token}")


@app.route('/songs')
def add_songs():
    token = request.args.get("token")
    if 'access_token' not in USER_SESSIONS[token]:
        return redirect('/login')
    
    if datetime.now().timestamp() > USER_SESSIONS[token]["expires_at"]:
        return redirect('/login')
    
    if 'playlist_id' not in USER_SESSIONS[token]:
        return "Playlist ID not found. Crea prima la playlist.", 400

    if 'tracks' not in USER_SESSIONS[token]:
        return "Tracks non presenti in sessione", 400
    
    headers = {
        'Authorization':f"Bearer {USER_SESSIONS[token]['access_token']}",
        "Content-Type": "application/json"
    }

    songs = USER_SESSIONS[token]['tracks']
    songs_final = [f"spotify:track:{i}" for i in songs]
        
    data = {
        "uris": songs_final
    }

    playlist_id = USER_SESSIONS[token]['playlist_id']
    response = requests.post(f"{API_BASE_URL}playlists/{playlist_id}/tracks", headers=headers, json=data)
    print("STATUS:", response.status_code)
    print("BODY:", response.text)
    try:
        res_json = response.json()
    except:
        return f"Errore Spotify (non JSON): {response.status_code}<br>{response.text}", 400
    
    del USER_SESSIONS[token]
    return "PLAYLIST COMPLETA, UN BACIO"


@app.route("/debug")
def debug():
    return {
        "CLIENT_ID": CLIENT_ID,
        "CLIENT_SECRET": CLIENT_SECRET,
        "REDIRECT_URI": REDIRECT_URI,
        "AUTH_URL": AUTH_URL,
        "TOKEN_URL": TOKEN_URL
    }

