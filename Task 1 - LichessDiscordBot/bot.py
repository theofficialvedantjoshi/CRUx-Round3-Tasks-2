import asyncio
import json
import os

import berserk
import chess
import discord
import lichess_client
import redis
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
r = redis.Redis(host="localhost", port=6379, db=0)

TOKEN = os.getenv("DISCORD_TOKEN")
intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.members = True
intents.messages = True
intents.guilds = True
intents.dm_messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


def get_auth(user_id) -> tuple:
    data = r.get(f"auth_{user_id}")
    if data is None:
        return None, None
    data = json.loads(data.decode("utf-8"))
    return data["token"], data["lichess_username"]


def render_board(fen: str) -> str:
    board = ""
    rows = fen.split(" ")[0].split("/")
    x_marks = ["1", "2", "3", "4", "5", "6", "7", "8"]
    y_marks = ["a", "b", "c", "d", "e", "f", "g", "h"]
    for row in rows:
        board += x_marks.pop(0) + "  "
        for char in row:
            if char.isdigit():
                board += " " * int(char) * 2
            else:
                board += " " + chess.UNICODE_PIECE_SYMBOLS[char] + " "
        board += "\n"
    board += "   " + "  ".join(y_marks) + "\n"
    return board


def generate_board(moves: list[str]) -> str:
    board = chess.Board()
    if moves is not None:
        for move in moves.split(" "):
            board.push(chess.Move.from_uci(move))
    return render_board(board.fen())


async def stream_game(ctx, game_id, client: lichess_client.APIClient):
    message = await ctx.send("Loading game...")
    async for event in client.boards.stream_game_state(game_id):
        print(event.entity.content)
        event = json.loads(event.entity.content)
        if event.get("status") in {"mate", "draw", "resign"}:
            result = f"Game over! {event['status'].capitalize()}."
            if event.get("winner"):
                result += f" Winner: {event['winner']}."
            await message.edit(content=result)
            break
        elif event.get("rematch", None):
            await message.edit(
                content="Rematch!\nJoin new game: "
                + "https://lichess.org/"
                + event["rematch"]
            )
            break
        moves = event.get("moves", None)
        board = generate_board(moves)
        await message.edit(content=board)


async def stream_events(ctx, client: lichess_client.APIClient):
    async for event in client.boards.stream_incoming_events():
        print(event)
        event = json.loads(event.entity.content)
        if event["type"] == "gameStart":
            r.set(f"game_{ctx.author.id}", event["game"]["id"])
            await ctx.send("Game started!")
            await ctx.send(f"Game ID: {event['game']['id']}")
            await ctx.send(f"{ctx.author.mention} playing as {event['game']['color']}")
            asyncio.create_task(stream_game(ctx, event["game"]["id"], client))


@bot.command(name="login")
async def login(ctx):
    user_id = ctx.author.id
    await ctx.send(f"I have sent you a DM with the login link.")
    await ctx.author.send(f"http://localhost:5000/login/{user_id}")


@bot.command(name="profile")
async def profile(ctx):
    user_id = ctx.author.id
    token, username = get_auth(user_id)
    if token is None:
        await ctx.send("You must login first.")
        return
    client = lichess_client.APIClient(token)
    account = await client.account.get_my_profile()
    account = json.loads(account.entity.content)
    print(account)
    await ctx.send(f"Hello {account['username']}!")


@bot.command(name="stream", help="Stream a game")
async def stream(ctx, game_id):
    user_id = ctx.author.id
    token, username = get_auth(user_id)
    if token is None:
        await ctx.send("You must login first.")
        return
    await ctx.send(f"Streaming game {game_id}")
    client = lichess_client.APIClient(token)
    r.set(f"game_{ctx.author.id}", game_id)
    asyncio.create_task(stream_game(ctx, game_id, client))


@bot.command(
    name="playai",
    help="Play against the AI <level> <clock_limit> <clock_increment> <color> <variant>",
)
async def playai(
    ctx, level=8, clock_limit=None, clock_increment=None, color=None, variant="standard"
):
    user_id = ctx.author.id
    token, username = get_auth(user_id)
    if token is None:
        await ctx.send("You must login first.")
        return
    if clock_limit is not None and clock_increment is not None:
        if clock_limit % 60 != 0 or clock_increment > 180:
            await ctx.send("Invalid time control")
            return
    token_session = berserk.TokenSession(token)
    client = berserk.Client(session=token_session)
    try:
        game = client.challenges.create_ai(
            level=int(level),
            clock_limit=int(clock_limit) if clock_limit else None,
            clock_increment=(
                int(clock_increment) if clock_increment is not None else None
            ),
            color=color,
            variant=variant,
        )
    except:
        await ctx.send("Invalid parameters.")
        return
    print(game)
    await ctx.send(
        f"Game created: https://lichess.org/{game['id']}\n You can play online or here on discord using the !stream and !move commands."
    )


@bot.command(name="move", help="Make a move in the current game")
async def move(ctx, move):
    print(move)
    user_id = ctx.author.id
    token, username = get_auth(user_id)
    if token is None:
        await ctx.send("You must login first.")
        return
    token_session = berserk.TokenSession(token)
    client = berserk.Client(session=token_session)
    game_id = r.get(f"game_{ctx.author.id}")
    if game_id is None:
        await ctx.send("No active game.")
        return
    game_id = game_id.decode("utf-8")
    print(game_id)
    if move == "resign":
        await ctx.send("Resigning the game.")
        client.board.resign_game(game_id)
    elif move == "draw":
        await ctx.send("Offering a draw.")
        client.board.offer_draw(game_id)
    else:
        try:
            client.board.make_move(game_id, move)
        except:
            await ctx.send("Invalid move.")
            return
        await ctx.send(f"Move made: {move}")


@bot.command(
    name="duel",
    help="Duel another player <user> <rated> <clock_limit> <clock_increment> <color> <variant>",
)
async def duel(
    ctx,
    user: discord.Member,
    rated=False,
    clock_limit=None,
    clock_increment=None,
    color=None,
    variant="standard",
):
    user_id = ctx.author.id
    token, username = get_auth(user_id)
    if token is None:
        await ctx.send("You must login first.")
        return
    if clock_limit is not None and clock_increment is not None:
        if clock_limit % 60 != 0 or clock_increment > 180:
            await ctx.send("Invalid time control")
            return
    rated = bool(int(rated)) if rated else False
    token_session = berserk.TokenSession(token)
    client = berserk.Client(session=token_session)
    oponent_token, oponent_username = get_auth(user.id)
    try:
        challenge = client.challenges.create(
            oponent_username,
            rated,
            clock_limit=int(clock_limit) if clock_limit else None,
            clock_increment=(
                int(clock_increment) if clock_increment is not None else None
            ),
            color=color,
            variant=variant,
        )
    except:
        await ctx.send("Invalid parameters.")
        return
    print(challenge)
    duel_message = await ctx.send(
        f"{user.mention} you have been challenged to a duel by {ctx.author.mention}.\nTo accept the challenge, reply to this message with !accept. To decline, reply with !decline."
    )
    r.set(f"challenge_{challenge['id']}", duel_message.id)


@bot.command(name="accept", help="Accept a challenge")
async def accept(ctx):
    if ctx.message.reference is None:
        await ctx.send("You must reply to a duel message.")
        return
    user_id = ctx.author.id
    token, username = get_auth(user_id)
    if token is None:
        await ctx.send("You must login first.")
        return

    token_session = berserk.TokenSession(token)
    client = berserk.Client(session=token_session)
    challenges = client.challenges.get_mine()
    challenge_id = next(
        (
            challenge["id"]
            for challenge in challenges["in"]
            if r.get(f"challenge_{challenge['id']}") == ctx.message.reference.message_id
        ),
        None,
    )
    if challenge_id is None:
        await ctx.send("Invalid challenge.")
        return
    try:
        client.challenges.accept(challenge_id)
        r.delete(f"challenge_{challenge_id}")
        await stream_events(ctx, client)
    except:
        await ctx.send("Invalid challenge.")
        return


@bot.command(name="decline", help="Decline a challenge")
async def decline(ctx, reason="generic"):
    if ctx.message.reference is None:
        await ctx.send("You must reply to a duel message.")
        return
    user_id = ctx.author.id
    token, username = get_auth(user_id)
    if token is None:
        await ctx.send("You must login first.")
        return

    token_session = berserk.TokenSession(token)
    client = berserk.Client(session=token_session)
    challenges = client.challenges.get_mine()
    challenge_id = next(
        (
            challenge["id"]
            for challenge in challenges["in"]
            if r.get(f"challenge_{challenge['id']}") == ctx.message.reference.message_id
        ),
        None,
    )
    if challenge_id is None:
        await ctx.send("Invalid challenge.")
        return
    try:
        client.challenges.decline(challenge_id)
        r.delete(f"challenge_{challenge_id}")
        await ctx.send("Challenge declined.")
    except:
        await ctx.send("Invalid challenge.")
        return


if __name__ == "__main__":
    bot.run(TOKEN)

# token = json.loads(r.get("auth_433582252790906891").decode("utf-8"))
# print(token)
# session = berserk.TokenSession(token["token"])
# client = berserk.Client(session=session)
# games = client.account.get()
# print(games)
