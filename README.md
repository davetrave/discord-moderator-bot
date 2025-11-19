# Discord Moderator Bot

This project is a Discord moderator bot built using the `discord.py` library. It provides various moderation commands to help manage a Discord server effectively.

## Features

- Kick, ban, mute, and warn users.
- Automatic message filtering based on a blacklist of words.
- Logging of moderation actions in a designated channel.
- Warning system to keep track of user infractions.

## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   cd discord-moderator-bot
   ```

2. Create a virtual environment (optional but recommended):
   ```
   python -m venv venv

   ```

   And then activate the virtual env
   **For unix systems**
   ```
      source venv/bin/activate 
   ```

   **For windows**
   ```
      venv\Scripts\activate
   ```


3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your Discord bot token:
   - Create a `.env` file or set the `DISCORD_TOKEN` environment variable with your bot token.

## Usage

1. Run the bot:
   ```
   python src/mybot.py
   ```
   Here, for production the whole folder can be placed under any project, and run the python script.It works on production server.

2. Create your invite url from discord 
   developer platform and add it to your server.

3. Type hello bot and the following text appears, set up is all DONE

   `Hello, {your name}! I am the moderator bot. \nType !modhelp to be familiar with my commands.`


4. Use the following commands in your Discord server:
   - `!kick @user [reason]` - Kick a user from the server.
   - `!ban @user [reason]` - Ban a user from the server.
   - `!mute @user [duration] [reason]` - Mute a user for a specified duration.
   - `!warn @user [reason]` - Warn a user for inappropriate behavior.
   - `!blacklist add [word]` - Add a word to the blacklist.
   - `!blacklist remove [word]` - Remove a word from the blacklist.
   - `!warnings @user` - View warnings for a user.

## Configuration

- The bot uses `warnings.json` to store user warnings and `blacklist.json` for blacklisted words. These files are located in the `data` directory. Remove the last `.template ` on the two files ext before use.