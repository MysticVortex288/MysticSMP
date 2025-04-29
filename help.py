
import discord
from discord.ext import commands

class HelpCog(commands.Cog, name="Hilfe"):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hilfe(self, ctx):
        embed = discord.Embed(
            title="🔍 Bot Befehle",
            description="Hier sind alle verfügbaren Befehle:",
            color=discord.Color.blue()
        )

        # Level System Kategorie
        embed.add_field(
            name="📊 Level System",
            value="""
`!profile` - Zeigt dein Level-Profil an
`!levelleaderboard` - Zeigt die Top 10 der aktivsten Nutzer
            """,
            inline=False
        )

        # Einladungs System Kategorie
        embed.add_field(
            name="📨 Einladungen",
            value="`!leaderboard` - Zeigt die Einladungs-Rangliste",
            inline=False
        )

        # Allgemeine Befehle
        embed.add_field(
            name="🛠️ Allgemein",
            value="`!ping` - Prüft ob der Bot online ist",
            inline=False
        )

        # Admin Befehle
        embed.add_field(
            name="👑 Admin Befehle",
            value="""
`!levelsetup <channel>` - Legt den Level-Up Benachrichtigungskanal fest
`!countingsetup <channel>` - Legt den Zählkanal fest
            """,
            inline=False
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
