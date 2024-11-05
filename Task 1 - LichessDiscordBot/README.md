# Chessify

A Chess Discord Bot integrated with Lichess API that allows users to play chess games, stream games, challenge ai and other users, create gifs of games, and more.

## Features

1. **OAuth Login**: Users can login to their Lichess account using OAuth.
2. **Play Chess**: Users can create games against the lichess AI or other users.
3. **Stream Games**: Users can stream games from Lichess. The bot updates the board in real-time.
4. **Play Moves**: Users can play moves(uci format) in their current game.
5. **Challenge Users**: Users can challenge other users to a game.
6. **Create Gifs**: Users can create gifs of their finished games.

## Setup

1. **Lichess API**:
   - Create your own `LICHESS_CLIENT_ID` and `LICHESS_CLIENT_SECRET`.
   - The Client ID can be any string of your choice.
   - The Client Secret should be a secure, URL-safe Base64 encoded string, 32 bytes in length.
   - Add these values to your `.env` file like this:

     ```ini
     LICHESS_CLIENT_ID=your_client_id
     LICHESS_CLIENT_SECRET=your_client_secret
     ```

2. **Redis**:
    - Install [Redis](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/install-redis-on-linux/) on your system.
    - Start the Redis server using `sudo service redis-server start`.

3. **Discord Bot**:

   Follow these steps to set up a Discord bot for your application:

   1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
   2. Click **New Application** and give your application a name.
   3. In your application’s settings, go to the **Bot** section and click **Add Bot**. Confirm the action to create your bot.
   4. Under the **Bot Permissions**:
      - The permission integer needed would be `10737937408`.
   5. Save your bot's token by copying it (you’ll need this token to run the bot) and add it to your `.env` file as follows:

      ```ini
      DISCORD_BOT_TOKEN=your_bot_token
      ```

   6. **Invite the Bot to Your Server**:
      - Generate an invite link for your bot.
      - Visit the link in your browser, select the server where you want to add the bot, and authorize it.
   7. With the bot added to your server, you can now run the bot.
      - Make sure all the required environment variables are set in your `.env` file.
      - Make sure all the required packages are installed using `pip install -r requirements.txt`.
      - Run the flask server for authentication using `python3 server.py`.
      - Run the bot using `python3 main.py`.

## Commands

All commands are organized under the `Chessify Commands` Cog, providing commands to connect with Lichess, initiate games, track progress, and animate completed games.

---

### Command List and Descriptions

#### `/login`

- **Description**: Connect your Lichess account to Chessify.
- **Usage**: `/login`
- **Details**: Sends the user a link in a DM to authorize the bot to access their Lichess account. If already connected, it notifies the user of their current Lichess username.

#### `/profile`

- **Description**: View your Lichess profile information.
- **Usage**: `/profile`
- **Details**: Displays a summary of the user’s Lichess profile, including their blitz rating, total games played, wins, losses, and draws. Users must be logged in with Lichess for this command to work.

#### `/playai`

- **Description**: Start a game against the Lichess AI.
- **Usage**: `/playai [level=8] [clock_limit=None] [clock_increment=None] [color=None] [variant=standard]`
- **Parameters**:
  - `level`: AI difficulty from 1 (easiest) to 8 (hardest). Default is 8.
  - `clock_limit`: Time control in minutes. Default is infinity.
  - `clock_increment`: Time increment in seconds (maximum 180).
  - `color`: User's color (white or black). Default is random.
  - `variant`: Game variant (standard, crazyhouse, chess960, etc.). Default is standard.
- **Details**: Creates a Lichess AI game based on provided settings, generating a game link for Lichess and inviting the user to play or use Chessify’s `/stream` and `/move` commands.

#### `/duel`

- **Description**: Challenge another Discord user to a game.
- **Usage**: `/duel @user [rated=False] [clock_limit=None] [clock_increment=None] [color=None] [variant=standard]`
- **Parameters**:
  - `user`: Discord user to challenge.
  - `rated`: Boolean to decide if the game should be rated. Default is False.
  - `clock_limit`: Time control in minutes. Default is infinity.
  - `clock_increment`: Time increment in seconds (maximum 180).
  - `color`: Player's color (white or black). Default is random.
  - `variant`: Game variant (standard, crazyhouse, chess960, etc.). Default is standard.
- **Details**: Challenges a specified Discord user. If the opponent has not connected their Lichess account, the bot notifies the challenger. The command creates a challenge message to which the opponent can respond using `/accept` or `/decline`.

#### `/stream`

- **Description**: Stream a game in progress.
- **Usage**: `/stream game_id`
- **Parameters**:
  - `game_id`: ID of the game to stream.
- **Details**: Starts streaming the specified game in the channel. The user must be logged in and have a valid game ID.

#### `/move`

- **Description**: Make a move in the current game.
- **Usage**: `/move move`
- **Parameters**:
  - `move`: UCI notation of the move or keywords "resign" or "draw".
- **Details**: Executes a move in the ongoing streamed game. If "resign" is used, the bot will resign the game; if "draw", it offers a draw to the opponent.

#### `/accept`

- **Description**: Accept a challenge by replying to the challenge message.
- **Usage**: `/accept`
- **Details**: Accepts a pending challenge. The user must reply to the original challenge message for this command to work.

#### `/decline`

- **Description**: Decline a challenge by replying to the challenge message.
- **Usage**: `/decline [reason="generic"]`
- **Parameters**:
  - `reason`: Optional reason for declining (e.g., "tooFast", "tooSlow", "timeControl").
- **Details**: Declines a pending challenge with an optional reason, which defaults to "generic".

#### `/create_gif`

- **Description**: Create an animated GIF of any completed game.
- **Usage**: `/create_gif game_id`
- **Parameters**:
  - `game_id`: The Lichess game ID to animate.
- **Details**: Generates a GIF of a completed Lichess game, displaying all moves played. The user must provide a valid game ID of a finished game.

---

### Tools used

- **Authentication**: Implemented OAuth2 for Lichess login using Flask.
- **Redis**: Used Redis for caching user data and game information.
- **Lichess API**: Utilized the sync and async Lichess API for game management.
- **Discord Bot**: Created a Discord bot using the discord.py library.
- **Chess Management**: Used the python chess module to manage chess games and generate GIFs.
- **Asynchronous Tasks**: Implemented async tasks for streaming games and creating GIFs.

### Todos

- [ ] Implement better async task handling for streaming events.
- [ ] Using ascii art to display the board in the stream command resulting in better usage of memory than storing images.
- [ ] Add more commands for game management.
- [ ] Improve lichess error handling and user feedback.