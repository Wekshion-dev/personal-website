import os

API_KEY = os.getenv("API_KEY", "")
STEAM_ID = os.getenv("STEAM_ID", "")

NETFETCH_PC_URL = os.getenv("NETFETCH_PC_URL", "")
NETFETCH_SERVER_URL = os.getenv("NETFETCH_SERVER_URL", "")
NETFETCH_TIMEOUT = float(os.getenv("NETFETCH_TIMEOUT", "3"))
NETFETCH_OUTPUT_PATH = os.getenv("NETFETCH_OUTPUT_PATH", "./public/data/specs.json")