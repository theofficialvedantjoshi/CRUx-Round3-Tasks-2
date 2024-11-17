import discord
from discord.ext import commands
from typing import Optional
import json
import discord.ext.commands
import discord.ext.commands.context as context
import redis
import berserk
import lichess_client
import asyncio
from board import generate_board, create_board_gif
import time
import async_timeout

import discord.ext

r = redis.Redis(host="localhost", port=6379, db=0)


def get_auth(user_id: int) -> tuple:
    data = r.get(f"auth_{user_id}")
    if data is None:
        return None, None
    data = json.loads(data.decode("utf-8"))
    return data["token"], data["lichess_username"]


async def stream_game(
    ctx: context, game_id: str, client: lichess_client.APIClient
) -> None:
    embed = discord.Embed(title="Game in progress")
    message = await ctx.send(embed=embed)
    async for event in client.boards.stream_game_state(game_id):
        print(event.entity.content)
        event = json.loads(event.entity.content)
        if event["type"] == "gameFull":
            white = event["white"].get("name") or f"AI lvl {event['white']['aiLevel']}"
            black = event["black"].get("name") or f"AI lvl {event['black']['aiLevel']}"
            await ctx.send(f"White: {white}\nBlack: {black}")
        if event.get("status") in {"mate", "draw", "resign"}:
            result = f"Game over! {event['status'].capitalize()}."
            if event.get("winner"):
                result += f" Winner: {event['winner']}."
            embed = discord.Embed(title=result)
            await message.edit(embed=embed)
            break
        elif event.get("rematch", None):
            embed = discord.Embed(
                title="Rematch!",
                description="Join the new game!",
                url=f"https://lichess.org/{event['rematch']}",
            )
            await message.edit(embed=embed)
            break
        moves = event.get("moves", None)
        board, image = generate_board(moves)
        await message.edit(embed=board, attachments=[image])


async def stream_events(
    ctx: context, client: lichess_client.APIClient, opponent: str, opponent_id: str
) -> None:

    try:
        with async_timeout.timeout(5):
            async for event in client.boards.stream_incoming_events():
                print(event)
                event = json.loads(event.entity.content)
    except asyncio.TimeoutError:
        if event["type"] == "gameStart" and event["game"]["opponent"]["id"] == opponent:
            r.set(f"game_{ctx.author.id}", event["game"]["id"])
            r.set(f"game_{opponent_id}", event["game"]["id"])
            await ctx.send("Game started!")
            await ctx.send(f"Game ID: {event['game']['id']}")
            await ctx.send(
                f"{ctx.author.mention} playInvalid challenge ID provided.g as {event['game']['color']}"
            )
            asyncio.create_task(stream_game(ctx, event["game"]["id"], client))
        else:
            await ctx.send("Game not found")


class Commands(commands.Cog, name="Chessify Commands"):
    def __init__(self, bot: discord.ext.commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="login")
    async def login(self, ctx: context):
        """Connect your Lichess account to use the bot"""
        token, username = get_auth(ctx.author.id)
        if token is not None:
            await ctx.send(f"Already logged in as {username}")
            return
        await ctx.send(
            embed=discord.Embed(
                title="Login to Lichess",
                description="I've sent you a DM with the login link!",
                color=discord.Color.blue(),
            ),
            ephemeral=True,
        )
        await ctx.author.send(
            f"Click here to connect your Lichess account: http://localhost:5000/login/{ctx.author.id}"
        )

    @commands.hybrid_command(name="profile")
    async def profile(self, ctx: context):
        """View your Lichess profile information"""
        token, _ = get_auth(ctx.author.id)
        if token is None:
            await ctx.respond(
                embed=discord.Embed(
                    title="Not Logged In",
                    description="Please use `/login` to connect your Lichess account first.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return
        session = berserk.TokenSession(token)
        client = berserk.Client(session)
        user = client.account.get()
        embed = discord.Embed(
            title=f"{user['username']}'s Profile",
            description=(
                f"Rating: {user['perfs']['blitz']['rating']}\n"
                f"Games Played: {user['count']['all']}\n"
                f"Wins: {user['count']['win']}\n"
                f"Losses: {user['count']['loss']}\n"
                f"Draws: {user['count']['draw']}"
            ),
            color=discord.Color.blue(),
        )
        embed.set_footer(text={user["url"]})
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="playai")
    async def playai(
        self,
        ctx: context,
        level: Optional[int] = 8,
        clock_limit: Optional[int] = None,
        clock_increment: Optional[int] = None,
        color: Optional[str] = None,
        variant: Optional[str] = "standard",
    ):
        """
        Start a game against the Lichess AI

        Parameters:
        -----------
        level: int
            AI difficulty (1-8), default: 8
        clock_limit: int
            Time control in minutes, default: ∞
        clock_increment: int
            Time increment in seconds (max 180)
        color: str
            Your color (white/black), default: random
        variant: str
            Game variant (standard/crazyhouse/chess960/etc), default: standard
        """
        token, _ = get_auth(ctx.author.id)
        if token is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Not Logged In",
                    description="Please use `/login` to connect your Lichess account first.",
                    color=discord.Color.red(),
                )
            )
            return
        session = berserk.TokenSession(token)
        client = berserk.Client(session)
        if clock_limit is not None and clock_increment is not None:
            clock_limit *= 60
            if clock_increment > 180:
                await ctx.send(
                    embed=discord.Embed(
                        title="Invalid Time Control",
                        description="Clock limit must be in minutes and increment must be ≤ 180 seconds",
                        color=discord.Color.red(),
                    )
                )
                return
        try:
            game = client.challenges.create_ai(
                level=level,
                clock_limit=clock_limit,
                clock_increment=clock_increment,
                color=color,
                variant=variant,
            )
            embed = discord.Embed(
                title="Game Created!",
                description=(
                    f"**Level:** AI Level {level}\n"
                    f"**Time Control:** {clock_limit if clock_limit else '∞'} + {clock_increment or 0}\n"
                    f"**Color:** {color or 'Random'}\n"
                    f"**Variant:** {variant.title()}\n"
                    f"**Game ID:** {game['id']}\n\n"
                    f"[Play on Lichess](https://lichess.org/{game['id']})\n"
                    "Or play here using `/stream` and `/move`"
                ),
                color=discord.Color.green(),
            )
            await ctx.send(embed=embed)
            r.set(f"game_{ctx.author.id}", game["id"])
        except Exception as e:
            await ctx.send(
                embed=discord.Embed(
                    title="Error Creating Game",
                    description="Invalid parameters provided. Please check the help command for details.",
                    color=discord.Color.red(),
                )
            )

    @commands.hybrid_command(name="duel")
    async def duel(
        self,
        ctx: context,
        user: discord.Member,
        rated: bool = False,
        clock_limit: Optional[int] = None,
        clock_increment: Optional[int] = None,
        color: Optional[str] = None,
        variant: str = "standard",
    ):
        """
        Challenge another Discord user to a game

        Parameters:
        -----------
        user: @mention
            The Discord user to challenge
        rated: bool
            Whether the game should be rated (True/False)
        clock_limit: int
            Time control in minutes, default: ∞
        clock_increment: int
            Time increment in seconds (max 180)
        color: str
            Your color (white/black), default: random
        variant: str
            Game variant (standard/crazyhouse/chess960/etc), default: standard
        """
        token, _ = get_auth(ctx.author.id)
        if token is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Not Logged In",
                    description="Please use `/login` to connect your Lichess account first.",
                    color=discord.Color.red(),
                )
            )
            return
        session = berserk.TokenSession(token)
        client = berserk.Client(session)
        opponent_token, opponent_username = get_auth(user.id)
        if opponent_token is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Opponent Not Logged In",
                    description="Your opponent has not connected their Lichess account.",
                    color=discord.Color.red(),
                )
            )
            return
        try:
            challenge = client.challenges.create(
                username=opponent_username,
                rated=rated,
                clock_limit=clock_limit,
                clock_increment=clock_increment,
                color=color,
                variant=variant,
            )
            duel_message = await ctx.send(
                embed=discord.Embed(
                    title="Chess Challenge!",
                    description=(
                        f"{user.mention}, you've been challenged by {ctx.author.mention}!\n\n"
                        f"**Rated:** {'Yes' if rated else 'No'}\n"
                        f"**Time Control:** {clock_limit//60 if clock_limit else '∞'}+{clock_increment or 0}\n"
                        f"**Variant:** {variant.title()}\n\n"
                        "Reply to this message with:\n"
                        "`accept` to accept the challenge\n"
                        "`decline` to decline"
                    ),
                    color=discord.Color.blue(),
                )
            )
            r.set(
                f"challenge_{challenge['id']}",
                json.dumps({"message_id": duel_message.id, "user_id": user.id}),
            )
        except Exception as e:
            print(e)
            await ctx.send(
                embed=discord.Embed(
                    title="Error Creating Challenge",
                    description="Invalid parameters provided. Please check the help command for details.",
                    color=discord.Color.red(),
                )
            )

    @commands.hybrid_command(name="stream")
    async def stream(self, ctx: context, game_id: str):
        """
        Stream a game in progress

        Parameters:
        -----------
        game_id: str
            The ID of the game to stream
        """
        print(game_id)
        token, _ = get_auth(ctx.author.id)
        if token is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Not Logged In",
                    description="Please use `/login` to connect your Lichess account first.",
                    color=discord.Color.red(),
                )
            )
            return
        client = lichess_client.APIClient(token)
        try:
            r.set(f"game_{ctx.author.id}", game_id)
            asyncio.create_task(stream_game(ctx, game_id, client))
        except Exception as e:
            await ctx.send(
                embed=discord.Embed(
                    title="Error Streaming Game",
                    description="Invalid game ID provided.",
                    color=discord.Color.red(),
                )
            )

    @commands.hybrid_command(name="move")
    async def move(self, ctx: context, move: str):
        """
        Make a move in the current game

        Parameters:
        -----------
        move: str in uci notation or "resign" or "draw".
        """
        token, _ = get_auth(ctx.author.id)
        if token is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Not Logged In",
                    description="Please use `/login` to connect your Lichess account first.",
                    color=discord.Color.red(),
                )
            )
            return
        session = berserk.TokenSession(token)
        client = berserk.Client(session)
        game_id = r.get(f"game_{ctx.author.id}")
        if game_id is None:
            await ctx.send(
                embed=discord.Embed(
                    title="No Game Stream",
                    description="You are not currently streaming a game.",
                    color=discord.Color.red(),
                )
            )
            return
        try:
            game_id = game_id.decode("utf-8")
            if move == "resign":
                client.board.resign_game(game_id)
                await ctx.send(
                    embed=discord.Embed(
                        title="Resigned",
                        description=f"{ctx.author.mention} has resigned the game.",
                        color=discord.Color.red(),
                    )
                )
            elif move == "draw":
                client.board.offer_draw(game_id)
                await ctx.send(
                    embed=discord.Embed(
                        title="Offered Draw",
                        description=f"{ctx.author.mention} has offered a draw.",
                        color=discord.Color.blue(),
                    )
                )
            else:
                client.board.make_move(game_id, move)
                await ctx.send(
                    embed=discord.Embed(
                        title="Move Made",
                        description=f"{ctx.author.mention} has made the move {move}",
                        color=discord.Color.green(),
                    )
                )
        except Exception as e:
            print(e)
            await ctx.send(
                embed=discord.Embed(
                    title="Error Making Move",
                    description="Invalid move provided.",
                    color=discord.Color.red(),
                )
            )

    @commands.command(name="accept")
    async def accept(self, ctx: context):
        """
        Accept a challenge by replying to the challenge message
        """
        token, _ = get_auth(ctx.author.id)
        if token is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Not Logged In",
                    description="Please use `/login` to connect your Lichess account first.",
                    color=discord.Color.red(),
                )
            )
            return
        session = berserk.TokenSession(token)
        client = berserk.Client(session)
        challenges = client.challenges.get_mine()
        print(challenges)
        challenge_id = None
        for challenge in challenges["in"]:
            data = json.loads(r.get(f"challenge_{challenge['id']}").decode("utf-8"))
            if data.get("message_id") == str(ctx.message.reference.message_id):
                challenge_id = challenge["id"]
                break
        if challenge_id is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Challenge Not Found",
                    description="No challenge found for this message.",
                    color=discord.Color.red(),
                )
            )
            return
        try:
            client = lichess_client.APIClient(token)
            await client.challenges.accept(challenge_id)
            opponent_user_id = json.loads(
                r.get(f"challenge_{challenge_id}").decode("utf-8")
            ).get("user_id")
            r.delete(f"challenge_{challenge_id}")
            await ctx.send(
                embed=discord.Embed(
                    title="Challenge Accepted",
                    description=f"{ctx.author.mention} has accepted the challenge.",
                    color=discord.Color.green(),
                )
            )
            asyncio.create_task(stream_events(ctx, client, opponent, opponent_user_id))
        except Exception as e:
            print(e)
            await ctx.send(
                embed=discord.Embed(
                    title="Error Accepting Challenge",
                    description="Invalid challenge ID provided.",
                    color=discord.Color.red(),
                )
            )

    @commands.command(name="decline")
    async def decline(self, ctx: context, reason: Optional[str] = "generic"):
        """
        Decline a challenge by replying to the challenge message

        Parameters:
        -----------
        reason: str (optional) - Reason for declining the challenge (generic, later, tooFast, tooSlow, timeControl, rated, casual, standard, variant, noBot, onlyBot) - default: generic
        """
        token, _ = get_auth(ctx.author.id)
        if token is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Not Logged In",
                    description="Please use `/login` to connect your Lichess account first.",
                    color=discord.Color.red(),
                )
            )
            return
        session = berserk.TokenSession(token)
        client = berserk.Client(session)
        challenges = client.challenges.get_mine()
        challenge_id = None
        for challenge in challenges["in"]:
            data = json.loads(r.get(f"challenge_{challenge['id']}").decode("utf-8"))
            if data.get("message_id") == str(ctx.message.reference.message_id):
                challenge_id = challenge["id"]
                break
        if challenge_id is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Challenge Not Found",
                    description="No challenge found for this message.",
                    color=discord.Color.red(),
                )
            )
            return
        try:
            client.challenges.decline(challenge_id, reason)
            r.delete(f"challenge_{challenge_id}")
            await ctx.send(
                embed=discord.Embed(
                    title="Challenge Declined",
                    description=f"{ctx.author.mention} has declined the challenge.",
                    color=discord.Color.red(),
                )
            )
        except Exception as e:
            await ctx.send(
                embed=discord.Embed(
                    title="Error Declining Challenge",
                    description="Invalid challenge ID provided.",
                    color=discord.Color.red(),
                )
            )

    @commands.hybrid_command(name="create_gif")
    async def create_gif(self, ctx: context, game_id: str):
        """
        Create an animated GIF of any completed game

        Parameters:
        -----------
        game_id: str
            The Lichess game ID to animate
        """
        token, _ = get_auth(ctx.author.id)
        if token is None:
            await ctx.send(
                embed=discord.Embed(
                    title="Not Logged In",
                    description="Please use `/login` to connect your Lichess account first.",
                    color=discord.Color.red(),
                )
            )
            return
        session = berserk.TokenSession(token)
        client = berserk.Client(session)
        try:
            game = client.games.export(game_id)
            moves = game["moves"]
            white = (
                f"AI lvl {game['players']['white']['aiLevel']}"
                if game["players"]["white"].get("aiLevel")
                else game["players"]["white"]["user"]["name"]
            )
            black = (
                f"AI lvl {game['players']['black']['aiLevel']}"
                if game["players"]["black"].get("aiLevel")
                else game["players"]["black"]["user"]["name"]
            )
            embed, image = create_board_gif(moves)
            embed.set_footer(text=f"{white} vs {black}")
            await ctx.send(embed=embed, file=image)
        except Exception as e:
            await ctx.send(
                embed=discord.Embed(
                    title="Error Fetching Game",
                    description="Invalid game ID provided.",
                    color=discord.Color.red(),
                )
            )
            return
