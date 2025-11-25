import discord
import discord.ui
from datetime import datetime

class ConfirmBanView(discord.ui.View):
    def __init__(self, guild: discord.Guild, target_member_id: int, *, timeout: int = 3600):
        super().__init__(timeout=timeout)
        self.guild = guild
        self.target_id = target_member_id

    async def _send_log(self, title: str, description: str):
        """Lightweight internal logger to mod-log (avoids importing mybot to prevent circular imports)."""
        try:
            embed = discord.Embed(title=title, description=description, color=discord.Color.blurple(), timestamp=datetime.utcnow())
            for ch in self.guild.text_channels:
                if ch.name == "mod-log" and ch.permissions_for(self.guild.me).send_messages:
                    try:
                        await ch.send(embed=embed)
                    except Exception:
                        pass
                    return
        except Exception:
            pass

    @discord.ui.button(label="Confirm Ban", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Only allow moderators (manage_guild) or users with a role named "moderator"/"mod" to confirm
        is_mod = interaction.user.guild_permissions.manage_guild or any(r.name.lower() in ("moderator", "mod", "mods") for r in interaction.user.roles)
        if not is_mod:
            await interaction.response.send_message("You are not authorized to confirm this ban.", ephemeral=True)
            return
        # fetch member
        member = self.guild.get_member(self.target_id)
        if not member:
            try:
                member = await self.guild.fetch_member(self.target_id)
            except discord.NotFound:
                await interaction.response.edit_message(content="Member not found; cannot ban.", view=None)
                return

        try:
            await self.guild.ban(member, reason=f"Auto-ban confirmed by {interaction.user}")
            await interaction.response.edit_message(content=f"✅ {member} was banned by {interaction.user}.", view=None)
            await self._send_log("Member Banned (Auto-confirm)", f"{member.mention} banned by {interaction.user.mention} after reaching 10 warnings.")
            self.stop()
        except Exception as e:
            await interaction.response.send_message(f"Failed to ban: {e}", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Ban canceled.", view=None)
        self.stop()
