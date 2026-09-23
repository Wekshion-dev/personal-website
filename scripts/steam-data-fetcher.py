import json
import requests
from VARS import API_KEY, STEAM_ID

url = 'https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/'

params = {
    "key": API_KEY,
    "steamid": STEAM_ID,
    "format": "json",
    "include_appinfo": "true",
    "include_played_free_games": "true",
}

needed_game_ids = {444200, 1422450, 427520, 294100, 367520, 1030300}

personal_descs = {
    444200: "Fkkk my life",
    1422450: "Game of the future",
    427520: "The factory must grow!",
    294100: "Almost as great as factorio",
    367520: "+vibe",
    1030300: "Some day I'll complete"
}

response = requests.get(url, params=params)

raw_data = response.json()

raw_games = raw_data.get("response", {}).get("games", [])
games = []
for i in raw_games:
    if i.get("appid") in needed_game_ids:
        i = {
            "appid": i.get("appid"),
            "id": i.get("name").lower().replace(" ", "-"),
            "name": i.get("name"),
            "playtime": round(float(i.get("playtime_forever")/60), 1),
            "img_icon_url": i.get("img_icon_url"),
            "description": personal_descs.get(i.get("appid"))
            }
        games.append(i)

games.sort(key=lambda x: x.get("playtime", 0), reverse=True)

with open("./public/data/games.json", "w", encoding="utf-8") as f:
    json.dump(games, f, ensure_ascii=False, indent=2)

