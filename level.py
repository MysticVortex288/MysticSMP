import discord
from discord.ext import commands
import json
import os

# XP-Daten und Level-Setup
xp_data = {}
level_up_channel_id = None  # Kanal-ID, in dem Level-Up-Nachrichten gesendet werden

# XP-Einstellungen (anpassbar)
xp_per_message = 10  # Wie viel XP pro Nachricht
xp_to_level_up = 100  # Wie viel XP man für das nächste Level benötigt

# Speichern der XP-Daten in einer Datei
def save_xp_data():
    with open("xp_data.json", "w") as f:
        json.dump(xp_data, f)

# Laden der XP-Daten
def load_xp_data():
    global xp_data
    if os.path.exists("xp_data.json"):
        with open("xp_data.json", "r") as f:
            xp_data = json.load(f)

class LevelingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_xp_data()  # XP-Daten laden

    @commands.command()
    @commands.has_permissions(administrator=True)  # Nur Admins können diesen Befehl ausführen
    async def levelsetup(self, ctx, channel: discord.TextChannel):
        """Admin-Befehl, um den Level-Up-Kanal festzulegen."""
        global level_up_channel_id
        level_up_channel_id = channel.id  # Speichern der Kanal-ID
        await ctx.send(f"✅ Der Level-Up Kanal wurde auf {channel.mention} gesetzt!")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        user_id = str(message.author.id)
        if user_id not in xp_data:
            xp_data[user_id] = 0  # Falls der Benutzer noch keine XP hat, initialisieren
        xp_data[user_id] += xp_per_message  # XP hinzufügen

        # Level-Up überprüfen
        await self.check_level_up(message.author)

        # Speichern der XP-Daten
        save_xp_data()

    async def check_level_up(self, member):
        user_xp = xp_data.get(str(member.id), 0)
        new_level = user_xp // xp_to_level_up

        # Abhängig vom Level eine Rolle vergeben und nur eine Nachricht senden, wenn das Level erreicht wurde
        roles = member.roles
        role_name = f"Level {new_level + 1}"  # Level beginnt bei 1

        # Check if the member hasn't already reached the next level
        if new_level >= 5 and "Level 5" not in [role.name for role in roles]:
            role = discord.utils.get(member.guild.roles, name="Level 5")
            if role:
                await member.add_roles(role)
                await member.send("🎉 Du hast Level 5 erreicht und eine neue Rolle erhalten!")

        if new_level >= 10 and "Level 10" not in [role.name for role in roles]:
            role = discord.utils.get(member.guild.roles, name="Level 10")
            if role:
                await member.add_roles(role)
                await member.send("🎉 Du hast Level 10 erreicht und eine neue Rolle erhalten!")

        # Check and notify only if the user has leveled up
        if level_up_channel_id:
            channel = self.bot.get_channel(level_up_channel_id)
            if channel:
                # Send a level up message only if the user has leveled up
                if user_xp // xp_to_level_up > (user_xp - xp_per_message) // xp_to_level_up:  # Check if level increased
                    await channel.send(f"🎉 {member.mention} hat Level {new_level + 1} erreicht! Glückwunsch!")

    @commands.command()
    async def levelleaderboard(self, ctx):
        """Zeigt das Level-Leaderboard an."""
        leaderboard = sorted(xp_data.items(), key=lambda x: x[1], reverse=True)
        embed = discord.Embed(
            title="🏆 Level Leaderboard",
            description="Hier ist das aktuelle Level-Leaderboard:",
            color=discord.Color.blue()
        )

        # Füge die Top 10 Mitglieder hinzu
        for index, (user_id, xp) in enumerate(leaderboard[:10]):
            user = self.bot.get_user(int(user_id))
            level = xp // xp_to_level_up
            embed.add_field(
                name=f"#{index + 1} - {user.name}",
                value=f"XP: {xp} | Level: {level + 1}",
                inline=False
            )

        await ctx.send(embed=embed)

    @commands.command()
    async def profile(self, ctx):
        """Zeigt das Profil des Benutzers mit seinen XP und Level an."""
        user_id = str(ctx.author.id)
        user_xp = xp_data.get(user_id, 0)
        user_level = user_xp // xp_to_level_up
        xp_remaining = xp_to_level_up - (user_xp % xp_to_level_up)

        embed = discord.Embed(
            title=f"👤 {ctx.author.name}'s Profil",
            description=f"Hier sind deine aktuellen XP und dein Fortschritt!",
            color=discord.Color.green()
        )

        embed.add_field(name="XP", value=f"{user_xp} XP", inline=False)
        embed.add_field(name="Level", value=f"Level {user_level + 1}", inline=False)
        embed.add_field(name="XP bis zum nächsten Level", value=f"{xp_remaining} XP", inline=False)

        await ctx.send(embed=embed)

# Cog laden
async def setup(bot):
    await bot.add_cog(LevelingCog(bot))  # Cog hinzufügen
