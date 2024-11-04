import discord
from discord.ext import commands
from commands import Commands


class Chessify(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents = discord.Intents.default()
        intents.typing = False
        intents.presences = False
        intents.members = True
        intents.messages = True
        intents.guilds = True
        intents.dm_messages = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.add_cog(Commands(self))

    async def on_ready(self):
        # get user by id
        user = await self.fetch_user(433582252790906891)
        # send message in users last texted channel


# token = json.loads(r.get("auth_433582252790906891").decode("utf-8"))
# print(token)
# session = berserk.TokenSession(token["token"])
# client = berserk.Client(session=session)
# games = client.account.get()
# print(games)
