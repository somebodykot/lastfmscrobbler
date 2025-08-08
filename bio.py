import os
import json
import getpass
import time
import requests
from telethon import TelegramClient, functions
import pylast

# Настройки Last.fm
API_KEY = "API_KEY"       # Insert your Last.fm API Key
API_SECRET = "API_KEY_SECRET" # Insert your Last.fm API Secret
SESSION_FILE = os.path.expanduser("~/..lastfm_session.json")
LASTFM_USER = None  # будет подставлен после входа

# Настройки Telegram
api_id = API_ID          # твой api_id
api_hash = 'AI_HASH'

# === Функции для работы с session key ===
def save_session_key(session_key, username):
    with open(SESSION_FILE, 'w') as f:
        json.dump({'session_key': session_key, 'username': username}, f)

def load_session_key():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            data = json.load(f)
            return data.get("session_key"), data.get("username")
    return None, None

def obtain_session_key():
    username = input("Last.fm username: ")
    password = getpass.getpass("Last.fm password: ")
    password_hash = pylast.md5(password)

    network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET)
    skg = pylast.SessionKeyGenerator(network)

    try:
        session_key = skg.get_session_key(username, password_hash)
        print("[INFO] Connected to Last.fm as", username)
        save_session_key(session_key, username)
        return session_key, username
    except Exception as e:
        print("[ERROR] Failed to get session_key:", e)
        return None, None

# === Получаем или загружаем session key ===
session_key, LASTFM_USER = load_session_key()
if not session_key or not LASTFM_USER:
    session_key, LASTFM_USER = obtain_session_key()
    if not session_key:
        print("Can't continue without Last.fm session key.")
        exit(1)

# Создаём объект сети last.fm с сессией
lastfm_network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET, session_key=session_key)

# === Telegram client ===
client = TelegramClient('tg_session', api_id, api_hash)

async def get_now_playing():
    try:
        user = lastfm_network.get_user(LASTFM_USER)
        track = user.get_now_playing()
        if track:
            artist = track.get_artist().get_name()
            title = track.get_title()
            return f"🎵 {artist} — {title}"
        else:
            return None
    except Exception as e:
        print("[ERROR] Last.fm get_now_playing:", e)
        return None

async def main():
    await client.start()
    last_bio = None
    while True:
        now_playing = await get_now_playing()
        if now_playing and now_playing != last_bio:
            try:
                await client(functions.account.UpdateProfileRequest(about=now_playing))
                print("Bio updated:", now_playing)
                last_bio = now_playing
            except Exception as e:
                print("Error updating bio:", e)
        await asyncio.sleep(60)

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
