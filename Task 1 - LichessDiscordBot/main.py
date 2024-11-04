import os

from bot import Chessify
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
bot = Chessify()
bot.run(TOKEN)
