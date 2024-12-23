from io import BytesIO

import chess
import discord
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from PIL import Image


def generate_board(moves: list[str]) -> str:
    board = chess.Board()
    if moves is not None:
        for move in moves.split(" "):
            board.push(chess.Move.from_uci(move))
    fig, ax = plt.subplots()
    ax.set_xlim([0, 8])
    ax.set_ylim([0, 8])
    ax.set_aspect("equal")
    ax.set_axis_off()
    for i in range(8):
        for j in range(8):
            if (i + j) % 2 == 0:
                color = "white"
            else:
                color = "gray"
            ax.add_patch(patches.Rectangle((i, j), 1, 1, color=color))
    for i in range(8):
        for j in range(8):
            piece = board.piece_at(chess.square(i, j))
            if piece is not None:
                ax.text(
                    i + 0.5,
                    j + 0.5,
                    chess.UNICODE_PIECE_SYMBOLS[piece.symbol()],
                    fontsize=30,
                    ha="center",
                    va="center",
                )
        ax.text(i + 0.5, -0.5, chess.FILE_NAMES[i], ha="center", va="center")
        ax.text(
            -0.5,
            i + 0.5,
            chess.RANK_NAMES[i],
            ha="center",
        )
    figure = fig.get_figure()
    buf = BytesIO()
    figure.savefig(buf, format="png")
    buf.seek(0)
    image = discord.File(buf, filename="board.png")
    buf.close()
    plt.clf()
    embed = discord.Embed(title="Game in progress", color=discord.Color.green())
    embed.set_image(url="attachment://board.png")
    return embed, image


def create_board_frame(board: chess.Board) -> Image.Image:
    fig, ax = plt.subplots()
    ax.set_xlim([0, 8])
    ax.set_ylim([0, 8])
    ax.set_aspect("equal")
    ax.set_axis_off()
    for i in range(8):
        for j in range(8):
            if (i + j) % 2 == 0:
                color = "white"
            else:
                color = "gray"
            ax.add_patch(patches.Rectangle((i, j), 1, 1, color=color))
    for i in range(8):
        for j in range(8):
            piece = board.piece_at(chess.square(i, j))
            if piece is not None:
                ax.text(
                    i + 0.5,
                    j + 0.5,
                    chess.UNICODE_PIECE_SYMBOLS[piece.symbol()],
                    fontsize=30,
                    ha="center",
                    va="center",
                )
        ax.text(i + 0.5, -0.5, chess.FILE_NAMES[i], ha="center", va="center")
        ax.text(
            -0.5,
            i + 0.5,
            chess.RANK_NAMES[i],
            ha="center",
        )
    figure = fig.get_figure()
    buf = BytesIO()
    figure.savefig(buf, format="png")
    buf.seek(0)
    plt.clf()
    return Image.open(buf)


def frame_generator(moves: list[str]):
    board = chess.Board()
    yield create_board_frame(board)
    for move in moves:
        board.push_san(move)
        yield create_board_frame(board)


def create_board_gif(moves: list[str]) -> tuple[discord.Embed, discord.File]:
    moves = moves.split()
    frames = list(frame_generator(moves))
    gif = BytesIO()
    frames[0].save(
        gif,
        save_all=True,
        append_images=frames[1:],
        duration=500,
        loop=0,
        format="GIF",
    )
    embed = discord.Embed(description="Match Replay", color=discord.Color.green())
    gif.seek(0)
    image = discord.File(gif, filename="replay.gif")
    embed.set_image(url="attachment://replay.gif")
    return embed, image
