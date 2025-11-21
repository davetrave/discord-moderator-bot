# Discord Moderator Bot

This project is a Discord moderator bot built using the `discord.py` library. It provides various moderation commands to help manage a Discord server effectively.

## Features

- Kick, ban, mute, unmute and warn users.
- Automatic message filtering based on a blacklist of words (auto-delete + auto-warn).
- Role management: create roles, assign/remove roles, add/remove roles from users.
- Channel moderation: lock/unlock channels and purge messages.
- Warning system to keep track of user infractions (persisted to disk).
- Logging of moderation actions in a designated channel (`mod-log`).
- Welcome messages for new members.
- Config and persistent data stored in the `data/` folder.
- Role utilities:
  - `!createrole` — create a role with optional color/hoist/mentionable options.
  - `!assign` / `!remove` — assign or remove an existing role by mention, ID, exact or partial name.
  - `!addrole` / `!removerole` — create a role and add/remove it from a member.
- Channel utilities:
  - `!lock` / `!unlock` — toggle send_messages for the @everyone role on a channel.
  - `!purge` — bulk-delete recent messages.
- Warnings:
  - `!warnings` — show warnings for a user.
  - `!clearwarns` — clear a user's warnings.
- Small help: `!modhelp` lists the moderation commands.
- Utilities in code:
  - Role creation / mute setup handled by [`ensure_muted_role`](src/mybot.py).
  - Warnings persisted and issued using [`warn_user`](src/mybot.py).
  - Moderation logs posted via [`log_action`](src/mybot.py).
- Logging channel: bot will create or use a channel named `mod-log` for action logs.

## Commands summary

- Basic: `!kick`, `!ban`, `!unban`, `!warn`, `!warnings`, `!clearwarns`
- Mute: `!mute [minutes] [reason]`, `!unmute`
- Roles: `!createrole`, `!assign`, `!remove`, `!addrole`, `!removerole`
- Channels: `!lock`, `!unlock`, `!purge`
- Blacklist: `!blacklist add <word>`, `!blacklist remove <word>`, `!blacklist` (list)
- Help: `!modhelp`

(Commands require the corresponding Discord permissions; the bot will respond if permissions are missing.)

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
   Activate it:
- On Unix:
  ```
  source venv/bin/activate
  ```
- On Windows:
  ```
  venv\Scripts\activate
  ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up your Discord bot token:
- Create a `.env` file or set the `DISCORD_TOKEN` environment variable with your bot token (see `.env.example`).

## Usage

1. Run the bot:
   ```
   python src/mybot.py
   ```
   Here, for production the whole folder can be placed under any project, and run the python script.It works on production server.

2. Invite the bot to your server via the invite url created from the Discord developer portal.

3. Interact in the server using the commands listed above. Example greeting:
- Send: `hello bot`
- Bot responds: "Hello, {your name}! I am the moderator bot. Type !modhelp to be familiar with my commands."

4. Use the following command usage examples
   - `!createrole Role Name [color:#hex] [hoist:yes/no] [mentionable:yes/no]` create a role in the guild without guild settings on Discord App.
   - `!assign @Trave @Moderator` - 
   - `!kick @user [reason]` - Kick a user from the server.
   - `!ban @user [reason]` - Ban a user from the server.
   - `!mute @user [duration] [reason]` - Mute a user for a specified duration.
   - `!warn @user [reason]` - Warn a user for inappropriate behavior.
   - `!blacklist add [word]` - Add a word to the blacklist.
   - `!blacklist remove [word]` - Remove a word from the blacklist.
   - `!warnings @user` - View warnings for a user.

## Data & configuration

- Persistent files are in the `data/` directory:
  - `data/warnings.json` — stores warnings per guild/user (see `data/warnings.json.template`).
  - `data/blacklist.json` — per-guild blacklist entries (see `data/blacklist.json.template`).
- Create the real files by copying the `.template` files or removing the `.template` suffix.

## Implementation references

- Main implementation and commands: [src/mybot.py](src/mybot.py)
- Key helper functions:
  - [`warn_user`](src/mybot.py)
  - [`ensure_muted_role`](src/mybot.py)
  - [`log_action`](src/mybot.py)

## Notes

- Ensure the bot has appropriate permissions (Manage Roles, Manage Channels, Manage Messages, Send Messages, etc.) for the features you want to use.
- The bot attempts to create a `Muted` role and set channel overwrites; if it cannot (role position/permissions), manual setup may be required.