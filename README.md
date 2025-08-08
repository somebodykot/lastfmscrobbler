```python
# Импорты
import os
import json
import time
import getpass
import dbus
import pylast

# API ключи от ластфм https://www.last.fm/api/account/create
API_KEY = "API_KEY"
API_SECRET = "API_SECRET" 

# Кеш авторизаций, удалите если хотите сбросить
SESSION_FILE = os.path.expanduser("~/.lastfm_session.json")

# Переменная для работы API ключей
network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET)

# Разрешённые плеера
ALLOWED_PLAYERS = [
# Яндекс
"org.mpris.MediaPlayer2.chromium.instance12735",
]
# Ну это тоже понятно
BLOCKED_PLAYERS = [
]

# Сохраниение кеша  / SESSION_FILE
def save_session_key(session_key):
	with open(SESSION_FILE, "w") as f:
		json.dump({"session_key": session_key}, f)

  
# Считывание кеша, если нет, кидает на логин
def load_session_key():
	if os.path.exists(SESSION_FILE):
		with open(SESSION_FILE, "r") as f:
			return json.load(f).get("session_key")
	return None

  
# Логин если нет кеша
def obtain_session_key():
	# Юзерка
	username = input("Last.fm username: ")
	# Пароль / можно поставить input [тогда будет видно пароль :)]
	password = getpass.getpass("Last.fm password: ")
	# для защиты пароля хеш
	password_hash = pylast.md5(password)

	skg = pylast.SessionKeyGenerator(network)
	
	try:
		session_key = skg.get_session_key(username, password_hash)
		print("[INFO] Connected to Last.fm as", username)
		save_session_key(session_key)
		return session_key
	except Exception as e:
		print("[ERROR] Failed to get session_key:", e)
	return None

# Получение актуального трека
def get_current_track():
	# Получение инфы о плеере
	session_bus = dbus.SessionBus()
	for service in session_bus.list_names():
	if service.startswith("org.mpris.MediaPlayer2.") and service in ALLOWED_PLAYERS:
		try:
			player = session_bus.get_object(service, "/org/mpris/MediaPlayer2")
			props = dbus.Interface(player, "org.freedesktop.DBus.Properties")
			metadata = props.Get("org.mpris.MediaPlayer2.Player", "Metadata")
			status = props.Get("org.mpris.MediaPlayer2.Player", "PlaybackStatus")
			# Проверка инфы
			if status.lower() == "playing":
				artist = str(metadata.get("xesam:artist", [""])[0])
				title = str(metadata.get("xesam:title", ""))
				length_microsec = metadata.get("mpris:length", 0)
				length_sec = length_microsec / 1_000_000 # секунды типо
				return service, artist, title, length_sec
		except:
			pass
	return None, None, None, 0

# Скроб в историю, и в now playing. А также вывод всей инфы в debug терминал.
def main():
	session_key = load_session_key()
	if not session_key:
		session_key = obtain_session_key()
		if not session_key:
		print("[ERROR] Could not get session_key. Exiting.")
		return

network = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET, session_key=session_key)

print("[INFO] Scrobbler started and connected.")

last_track = None
last_player = None
track_start_time = None
track_length = 0
scrobbled = False

while True:
	try:
		player, artist, title, length_sec = get_current_track()
		if player is None:
			if last_player is not None:
			print("[INFO] No allowed MPRIS players found.")
			last_player = None
			track_start_time = None
			scrobbled = False
	else:
		if last_player != player:
			print(f"[INFO] Found player: {player}")
			last_player = player
		if artist and title:
			track_id = f"{artist} - {title}"
			if track_id != last_track:
				print(f"[INFO] Now playing: {artist} — {title}")
				try:
					network.update_now_playing(artist=artist, title=title)
					last_track = track_id
					track_start_time = time.time()
					track_length = length_sec
					scrobbled = False
				except Exception as e:
					print(f"[ERROR] Failed to send now playing: {e}")
			else:
				# Чекер для того, пойдёт ли трек в скроб
				if not scrobbled and track_start_time and track_length > 0:
					elapsed = time.time() - track_start_time
				# Минимум 5 (вроде :]) минуты или 50% трека
				if elapsed >= 300 or elapsed >= (track_length / 2):
					try:
						timestamp = int(track_start_time)
						network.scrobble(artist=artist, title=title, timestamp=timestamp)
						print(f"[INFO] Scrobbled: {artist} — {title}")
						scrobbled = True
					except Exception as e:
						print(f"[ERROR] Failed to scrobble track: {e}")
	time.sleep(10)
except Exception as e:
	print(f"[ERROR] Main loop error: {e}")
	time.sleep(5)

if __name__ == "__main__":
	main()
```
