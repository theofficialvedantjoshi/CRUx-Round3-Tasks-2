import os

from bot import Chessify
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
bot = Chessify()
bot.run(TOKEN)
# import redis


# r = redis.Redis(host="localhost", port=6379, db=0)


# print(r.get("game_1302997915576569938").decode("utf-8"))
# print(r.get("game_433582252790906891").decode("utf-8"))
