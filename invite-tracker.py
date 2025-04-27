import discord
from discord.ext import commands

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Einladungen abrufen
        invites = await member.guild.invites()

        # Überprüfen, wer die Einladung gemacht hat
        for invite in invites:
            if invite.uses > invite.max_uses:
                inviter_name = invite.inviter.name
                inviter_avatar = invite.inviter.avatar.url  # Hier war der Fehler
                message = f"**{member.name}** wurde von **{invite.inviter}** eingeladen!"
                break
        else:
            inviter_name = "Unbekannt"
            inviter_avatar = None
            message = f"**{member.name}** wurde nicht von jemandem eingeladen."

        # Erstellen der Embed-Nachricht
        embed = discord.Embed(
            title="Willkommen im Server: Rainbow_Cat_Party! 🎉",
            description=message,
            color=discord.Color.green()  # Du kannst auch andere Farben wie red() oder blue() wählen
        )

        # Füge das Avatar des Einladers hinzu, wenn vorhanden
        if inviter_avatar:
            embed.set_thumbnail(url=inviter_avatar)

        # Fügt Emojis zur Embed-Nachricht hinzu
        embed.add_field(name="🎉 Einladung", value=f"Einladung von: {inviter_name}", inline=False)
        embed.add_field(name="🕒 Beitrittszeit", value=f"Beigetreten am: {member.joined_at.strftime('%d.%m.%Y, %H:%M')}", inline=True)

        # Bestimmte Channel angeben (hier nach Name suchen)
        channel = discord.utils.get(member.guild.text_channels, name='allgemein')  # Oder den gewünschten Channel
        if channel:
            await channel.send(embed=embed)

    # Leaderboard für Einladungen
    @commands.command()
    async def leaderboard(self, ctx):
        invites = await ctx.guild.invites()
        invites = sorted(invites, key=lambda invite: invite.uses, reverse=True)  # Sorting by most uses
        leaderboard_message = ""

        for i, invite in enumerate(invites):
            leaderboard_message += f"{i+1}. **{invite.inviter}** - {invite.uses} Einladungen\n"

        # Eine schönere Formatierung für das Leaderboard
        embed = discord.Embed(
            title="🏆 Einladung Leaderboard 🏆",
            description=leaderboard_message,
            color=discord.Color.blue()  # Blau für das Leaderboard
        )

        await ctx.send(embed=embed)

# Cog laden
async def setup(bot):
    await bot.add_cog(InviteTracker(bot))  # Mit await
