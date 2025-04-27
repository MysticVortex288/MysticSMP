import discord
from discord.ext import commands
import os

# Intents einstellen
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Wichtiger Intent, um Mitglieder-Events wie on_member_join zu verfolgen

# Bot erstellen
bot = commands.Bot(command_prefix="!", intents=intents)

# Event: Wenn der Bot bereit ist
@bot.event
async def on_ready():
    print(f"✅ Bot ist online! Eingeloggt als {bot.user}")

    # Cog laden
async def load_extensions():
    await bot.load_extension("invite-tracker")
    await bot.load_extension("verify")
    print("✅ Alle Cogs geladen.")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

# Bot starten
TOKEN = os.environ.get("DISCORD_TOKEN")  # Token kommt aus den Railway Environment Variables
bot.run(TOKEN)
