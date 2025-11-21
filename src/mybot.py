# filepath: /discord-moderator-bot/discord-moderator-bot/src/mybot.py
import os
import json
import asyncio
from datetime import datetime
from typing import Optional
import discord
from discord.ext import commands
from dotenv import load_dotenv
import difflib

load_dotenv()  # loads .env in project root into environment

# ---------- Configuration ----------
PREFIX = "!"
WARNINGS_FILE = "../data/warnings.json"
BLACKLIST_FILE = "../data/blacklist.json"
LOG_CHANNEL_NAME = "mod-log"
MUTED_ROLE_NAME = "Muted"
AUTO_DELETE_IN_SECONDS = 5  # how long to keep auto-deleted messages in DM notifications, not needed by Discord API
# -----------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=commands.MinimalHelpCommand())

# Load / save helpers
def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

warnings_db = load_json(WARNINGS_FILE, {})  # structure: {guild_id: {user_id: [ {by, reason, time}, ... ] } }
blacklists = load_json(BLACKLIST_FILE, {})  # structure: {guild_id: [word1, word2]}

# Utility: get or create mod-log channel
async def get_mod_log(guild: discord.Guild) -> Optional[discord.TextChannel]:
    for ch in guild.text_channels:
        if ch.name == LOG_CHANNEL_NAME:
            return ch
    # create channel if bot has perms
    try:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False, view_channel=True)
        }
        ch = await guild.create_text_channel(LOG_CHANNEL_NAME, overwrites=None)
        return ch
    except Exception:
        return None

# Utility: ensure muted role exists and has correct perms
async def ensure_muted_role(guild: discord.Guild) -> Optional[discord.Role]:
    role = discord.utils.get(guild.roles, name=MUTED_ROLE_NAME)
    if role:
        return role
    try:
        role = await guild.create_role(name=MUTED_ROLE_NAME, reason="Create muted role for moderation bot")
        # set channel overwrites to prevent sending messages for the role
        for channel in guild.channels:
            try:
                if isinstance(channel, (discord.TextChannel, discord.VoiceChannel, discord.Thread)):
                    await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
            except Exception:
                pass
        return role
    except Exception:
        return None

async def log_action(guild: discord.Guild, title: str, description: str):
    ch = await get_mod_log(guild)
    if ch:
        embed = discord.Embed(title=title, description=description, color=discord.Color.blurple(), timestamp=datetime.utcnow())
        try:
            await ch.send(embed=embed)
        except Exception:
            pass

# ---------------- Commands ----------------

@bot.event
async def on_ready():
    print(f"Bot ready as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_guild_join(guild):
    # Initialize defaults for new guild
    warnings_db.setdefault(str(guild.id), {})
    blacklists.setdefault(str(guild.id), [])
    save_json(WARNINGS_FILE, warnings_db)
    save_json(BLACKLIST_FILE, blacklists)

@bot.event
async def on_message(message: discord.Message):
    print(f"Message from {message.author} in {message.guild}: {message.content}\n")  # debug
    if message.author.bot:
        return
    
    if message.content and message.guild and not message.content.startswith(PREFIX):
        # The bot will send a greeting message in the channel where the user posted
        if message.content.lower().startswith("hello bot"):
            response = f"Hello, {message.author.display_name}! I am the moderator bot. \nType !modhelp to be familiar with my commands."
            await message.channel.send(response)

    guild = message.guild
    if guild:
        gkey = str(guild.id)
        bl = blacklists.get(gkey, [])
        content = (message.content or "").lower()
        trigger = None
        for bad in bl:
            if bad and bad.lower() in content:
                trigger = bad
                break
        if trigger:
            try:
                await message.delete()
            except Exception:
                pass
            # warn the user automatically
            await warn_user(guild, message.author, None, f"Auto-moderation: used blocked word '{trigger}'")
            await log_action(guild, "Auto-moderation", f"Deleted message from {message.author.mention} containing blocked word '{trigger}'.")
            try:
                await message.author.send(f"Your message in {guild.name} was removed for containing a blocked word.")
            except Exception:
                pass

    await bot.process_commands(message)

# ———————— welcome new members ————————
@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild
    print(f"New member joined: {member} in {guild.name}")
    print(f"Guild has {guild.member_count} members now.")
    print("Attempting to send welcome message...")
    print(f"Guild Channels = {guild.text_channels}")
    # 1. Try to find the most recently active text channel
    target_channel = None
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            try:
                async for msg in channel.history(limit=1):
                    if msg.author != bot.user:  # ignore bot's own messages
                        target_channel = channel
                        break
            except:
                continue
        if target_channel:
            break

    # 2. Fallback: system channel → default channel → first writable channel
    if not target_channel:
        target_channel = guild.system_channel
    if not target_channel:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                target_channel = ch
                break

    # 3. Send the welcome message
    if target_channel:
        welcome_text = f"🎉 Everyone welcome {member.mention} to **{guild.name}**! Say hi! 👋"
        try:
            await target_channel.send(welcome_text)
        except:
            pass  # silently fail if something weird happens

    # 4. Optional: Still log to mod-log
    await log_action(guild, "Member Joined", f"{member.mention} (`{member.id}`) joined the server. Total members: {guild.member_count}")

    # 5. Optional: DM the new member (comment if you needed)
    
    try:
        await member.send(f"Welcome to **{guild.name}**! 🎉\nHave fun and follow the rules!")
    except:
        pass
    


# Helper to add a warning
async def warn_user(guild: discord.Guild, user: discord.Member, moderator: Optional[discord.Member], reason: str):
    gkey = str(guild.id)
    ukey = str(user.id)
    warnings_db.setdefault(gkey, {})
    warnings_db[gkey].setdefault(ukey, [])
    entry = {
        "by": moderator.id if moderator else None,
        "by_name": moderator.name if moderator else "Auto",
        "reason": reason,
        "time": datetime.utcnow().isoformat()
    }
    warnings_db[gkey][ukey].append(entry)
    save_json(WARNINGS_FILE, warnings_db)
    await log_action(guild, "Warn Issued", f"{user.mention} was warned by {entry['by_name']}: {reason}")

# Basic moderation commands require appropriate permissions

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def cmd_kick(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"{member} has been kicked. Reason: {reason}")
        await log_action(ctx.guild, "Member Kicked", f"{member.mention} kicked by {ctx.author.mention}. Reason: {reason}")
    except Exception as e:
        await ctx.send(f"Failed to kick: {e}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def cmd_ban(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"{member} has been banned. Reason: {reason}")
        await log_action(ctx.guild, "Member Banned", f"{member.mention} banned by {ctx.author.mention}. Reason: {reason}")
    except Exception as e:
        await ctx.send(f"Failed to ban: {e}")

@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def cmd_unban(ctx, *, user: str):
    # user input like "username#1234"
    try:
        name, discrim = user.split("#")
    except ValueError:
        await ctx.send("Use format: username#discriminator")
        return
    bans = await ctx.guild.bans()
    for ban_entry in bans:
        if (ban_entry.user.name, ban_entry.user.discriminator) == (name, discrim):
            await ctx.guild.unban(ban_entry.user)
            await ctx.send(f"Unbanned {ban_entry.user}")
            await log_action(ctx.guild, "Member Unbanned", f"{ban_entry.user} unbanned by {ctx.author.mention}")
            return
    await ctx.send("User not found in ban list.")

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def cmd_mute(ctx, member: discord.Member, duration: Optional[int] = None, *, reason: str = "No reason provided"):
    role = await ensure_muted_role(ctx.guild)
    if not role:
        await ctx.send("Unable to create/find Muted role. Ensure the bot has Manage Roles permission.")
        return
    try:
        await member.add_roles(role, reason=reason)
        await ctx.send(f"{member.mention} has been muted. Reason: {reason}")
        await log_action(ctx.guild, "Member Muted", f"{member.mention} muted by {ctx.author.mention}. Reason: {reason}")
        if duration and duration > 0:
            await asyncio.sleep(duration * 60)
            # check if still muted
            if role in member.roles:
                try:
                    await member.remove_roles(role, reason="Auto unmute after duration")
                    await log_action(ctx.guild, "Member Unmuted", f"{member.mention} auto-unmuted after {duration} minutes.")
                except Exception:
                    pass
    except Exception as e:
        await ctx.send(f"Failed to mute: {e}")

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def cmd_unmute(ctx, member: discord.Member):
    role = discord.utils.get(ctx.guild.roles, name=MUTED_ROLE_NAME)
    if not role:
        await ctx.send("Muted role doesn't exist.")
        return
    try:
        await member.remove_roles(role)
        await ctx.send(f"{member.mention} has been unmuted.")
        await log_action(ctx.guild, "Member Unmuted", f"{member.mention} unmuted by {ctx.author.mention}.")
    except Exception as e:
        await ctx.send(f"Failed to unmute: {e}")

@bot.command(name="warn")
@commands.has_permissions(kick_members=True)
async def cmd_warn(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    await warn_user(ctx.guild, member, ctx.author, reason)
    await ctx.send(f"{member.mention} has been warned. Reason: {reason}")

@bot.command(name="warnings")
@commands.has_permissions(kick_members=True)
async def cmd_warnings(ctx, member: discord.Member):
    gkey = str(ctx.guild.id)
    ukey = str(member.id)
    user_warnings = warnings_db.get(gkey, {}).get(ukey, [])
    if not user_warnings:
        await ctx.send(f"{member.mention} has no warnings.")
        return
    lines = []
    for i, w in enumerate(user_warnings, 1):
        lines.append(f"{i}. {w['reason']} — by {w.get('by_name','Unknown')} at {w['time']}")
    # send in chunks if long
    text = "\n".join(lines)
    await ctx.send(f"Warnings for {member.mention}:\n{text}")

@bot.command(name="clearwarns")
@commands.has_permissions(kick_members=True)
async def cmd_clearwarns(ctx, member: discord.Member):
    gkey = str(ctx.guild.id)
    ukey = str(member.id)
    if gkey in warnings_db and ukey in warnings_db[gkey]:
        warnings_db[gkey][ukey] = []
        save_json(WARNINGS_FILE, warnings_db)
        await ctx.send(f"Cleared warnings for {member.mention}.")
        await log_action(ctx.guild, "Warnings Cleared", f"Warnings for {member.mention} cleared by {ctx.author.mention}.")
    else:
        await ctx.send("No warnings to clear.")

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def cmd_purge(ctx, amount: int = 10):
    if amount < 1 or amount > 100:
        await ctx.send("Amount must be between 1 and 100.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
    await ctx.send(f"Deleted {len(deleted)-1} messages.", delete_after=5)
    await log_action(ctx.guild, "Messages Purged", f"{ctx.author.mention} purged {len(deleted)-1} messages in {ctx.channel.mention}")

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def cmd_lock(ctx, channel: Optional[discord.TextChannel] = None):
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    try:
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"Locked {channel.mention}.")
        await log_action(ctx.guild, "Channel Locked", f"{channel.mention} locked by {ctx.author.mention}.")
    except Exception as e:
        await ctx.send(f"Failed to lock: {e}")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def cmd_unlock(ctx, channel: Optional[discord.TextChannel] = None):
    channel = channel or ctx.channel
    overwrite = channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    try:
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        await ctx.send(f"Unlocked {channel.mention}.")
        await log_action(ctx.guild, "Channel Unlocked", f"{channel.mention} unlocked by {ctx.author.mention}.")
    except Exception as e:
        await ctx.send(f"Failed to unlock: {e}")

@bot.command(name="createrole")
@commands.has_permissions(manage_roles=True)
async def cmd_createrole(ctx, *, role_name_and_options: str = None):
    """
    Creates a new role with optional settings.
    Usage examples:
      !createrole Moderator
      !createrole Admin color:#ff0000 hoist:yes mentionable:yes
      !createrole Verified color:green
      !createrole Muted color:#2f3136 hoist:no
    """
    if not role_name_and_options:
        return await ctx.send("Usage: `!createrole Role Name [color:#hex] [hoist:yes/no] [mentionable:yes/no]`")

    # Split name and options
    parts = role_name_and_options.strip().split()
    role_name = parts[0]
    options = " ".join(parts[1:]).lower()

    # Default values
    color = discord.Color.default()
    hoist = False
    mentionable = False

    # Parse options
    if "color:" in options:
        hex_part = options.split("color:")[1].split()[0]
        try:
            if hex_part.startswith("#"):
                color = discord.Color(int(hex_part[1:], 16))
            elif hex_part in ["red", "green", "blue", "purple", "orange", "gold", "blurple", "grey"]:
                color = getattr(discord.Color, hex_part)()
            else:
                color = discord.Color(int(hex_part, 16))
        except:
            color = discord.Color.random()

    if "hoist:yes" in options:
        hoist = True
    if "mentionable:yes" in options:
        mentionable = True

    # Create the role
    try:
        new_role = await ctx.guild.create_role(
            name=role_name,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
            reason=f"Created by {ctx.author}"
        )
        await ctx.send(f"Role **{new_role.name}** created successfully! {new_role.mention}")
        await log_action(ctx.guild, "Role Created", f"{ctx.author.mention} created role **{new_role.name}**")
    except discord.Forbidden:
        await ctx.send("I don't have permission to create roles. Move my role higher!")
    except Exception as e:
        await ctx.send(f"Failed: {e}")

# ———————— ASSIGN ROLE (Give any role to a user) ————————
@bot.command(name="assign")
@commands.has_permissions(manage_roles=True)
async def cmd_assign(ctx, member: discord.Member, *, role_name: str):
    """
    Usage: !assign @User Role Name
    Accepts role mention, role ID, exact case-insensitive name or partial name.
    """
    # Try role by mention / id
    role = None
    # role mention format: <@&id>
    if role_name.strip().startswith("<@&") and role_name.strip().endswith(">"):
        try:
            rid = int(role_name.strip()[3:-1])
            role = ctx.guild.get_role(rid)
        except Exception:
            role = None
    # numeric id
    if role is None and role_name.strip().isdigit():
        role = ctx.guild.get_role(int(role_name.strip()))
    # exact case-insensitive match
    if role is None:
        role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), ctx.guild.roles)
    # partial case-insensitive match (first match)
    if role is None:
        role = discord.utils.find(lambda r: role_name.lower() in r.name.lower(), ctx.guild.roles)
    # fallback: suggest close matches
    if role is None:
        names = [r.name for r in ctx.guild.roles]
        close = difflib.get_close_matches(role_name, names, n=3, cutoff=0.5)
        if close:
            return await ctx.send(f"❌ Role `{role_name}` not found. Did you mean: {', '.join(close)} ?")
        return await ctx.send(f"❌ Role `{role_name}` not found. Check spelling/capitalization or use role mention/ID.")
    
    # permission/position checks
    if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send("❌ You cannot assign a role that is higher than or equal to your highest role.")
    
    if role >= ctx.me.top_role:
        return await ctx.send("❌ I cannot assign this role because it is higher than or equal to my highest role.")
    
    try:
        await member.add_roles(role, reason=f"Assigned by {ctx.author}")
        await ctx.send(f"✅ Successfully gave **{role.name}** to {member.mention}")
        await log_action(ctx.guild, "Role Assigned", 
                        f"{member.mention} was given **{role.name}** by {ctx.author.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage that role.")

# ———————— REMOVE ROLE (Take any role from a user) ————————
@bot.command(name="remove")
@commands.has_permissions(manage_roles=True)
async def cmd_remove(ctx, member: discord.Member, *, role_name: str):
    """
    Usage: !remove @User Role Name
    Removes the exact role from the user.
    """
    role = discord.utils.find(lambda r: r.name.lower() == role_name.lower(), ctx.guild.roles)
    
    if not role:
        return await ctx.send(f"❌ Role `{role_name}` not found.")
    
    if role not in member.roles:
        return await ctx.send(f"❌ {member.mention} doesn't have the role **{role.name}**.")
    
    try:
        await member.remove_roles(role, reason=f"Removed by {ctx.author}")
        await ctx.send(f"✅ Successfully removed **{role.name}** from {member.mention}")
        await log_action(ctx.guild, "Role Removed", 
                        f"**{role.name}** was removed from {member.mention} by {ctx.author.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage that role.")

@bot.command(name="addrole")
@commands.has_permissions(manage_roles=True)
async def cmd_addrole(ctx, member: discord.Member, *, rolename: str):
    role = discord.utils.get(ctx.guild.roles, name=rolename)
    if not role:
        try:
            role = await ctx.guild.create_role(name=rolename, reason=f"Role created by {ctx.author}")
        except Exception as e:
            await ctx.send(f"Failed to create role: {e}")
            return
    try:
        await member.add_roles(role)
        await ctx.send(f"Added role {role.name} to {member.mention}.")
        await log_action(ctx.guild, "Role Added", f"Added role {role.name} to {member.mention} by {ctx.author.mention}.")
    except Exception as e:
        await ctx.send(f"Failed to add role: {e}")

@bot.command(name="removerole")
@commands.has_permissions(manage_roles=True)
async def cmd_removerole(ctx, member: discord.Member, *, rolename: str):
    role = discord.utils.get(ctx.guild.roles, name=rolename)
    if not role:
        await ctx.send("Role not found.")
        return
    try:
        await member.remove_roles(role)
        await ctx.send(f"Removed role {role.name} from {member.mention}.")
        await log_action(ctx.guild, "Role Removed", f"Removed role {role.name} from {member.mention} by {ctx.author.mention}.")
    except Exception as e:
        await ctx.send(f"Failed to remove role: {e}")

# Blacklist management
@bot.group(name="blacklist", invoke_without_command=True)
@commands.has_permissions(manage_guild=True)
async def cmd_blacklist(ctx):
    bl = blacklists.get(str(ctx.guild.id), [])
    if not bl:
        await ctx.send("No blacklisted words.")
    else:
        await ctx.send("Blacklisted words: " + ", ".join(bl))

@cmd_blacklist.command(name="add")
@commands.has_permissions(manage_guild=True)
async def cmd_blacklist_add(ctx, *, word: str):
    gkey = str(ctx.guild.id)
    blacklists.setdefault(gkey, [])
    if word.lower() in (w.lower() for w in blacklists[gkey]):
        await ctx.send("Word already blacklisted.")
        return
    blacklists[gkey].append(word)
    save_json(BLACKLIST_FILE, blacklists)
    await ctx.send(f"Added '{word}' to blacklist.")
    await log_action(ctx.guild, "Blacklist Added", f"'{word}' added to blacklist by {ctx.author.mention}")

@cmd_blacklist.command(name="remove")
@commands.has_permissions(manage_guild=True)
async def cmd_blacklist_remove(ctx, *, word: str):
    gkey = str(ctx.guild.id)
    if word in blacklists.get(gkey, []):
        blacklists[gkey].remove(word)
        save_json(BLACKLIST_FILE, blacklists)
        await ctx.send(f"Removed '{word}' from blacklist.")
        await log_action(ctx.guild, "Blacklist Removed", f"'{word}' removed from blacklist by {ctx.author.mention}")
    else:
        await ctx.send("Word not found in blacklist.")

# Small help override to show basic commands
@bot.command(name="modhelp")
async def cmd_help(ctx):
    text = (
        f"Moderation commands (prefix {PREFIX}):\n"
        "kick/ban/unban/mute/unmute/warn/warnings/clearwarns\n"
        "purge/lock/unlock/addrole/removerole\n"
        "blacklist add/remove/list\n"
    )
    await ctx.send(text)

# Error handlers
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing argument for command.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Bad argument type passed.")
    else:
        # fallback - log to mod channel if possible
        await log_action(ctx.guild or ctx.author, "Command Error", f"Error running command {ctx.command}: {error}")
        await ctx.send(f"An error occurred: {error}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Set the DISCORD_TOKEN environment variable and re-run.")
    else:
        bot.run(token)