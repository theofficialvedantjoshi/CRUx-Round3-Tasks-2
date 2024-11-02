from io import BytesIO

import chess
import discord
import matplotlib.patches as patches
import matplotlib.pyplot as plt


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
    plt.clf()
    embed = discord.Embed(title="Game in progress", color=discord.Color.green())
    embed.set_image(url="attachment://board.png")
    return embed, image
