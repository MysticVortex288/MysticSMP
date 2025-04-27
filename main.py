import discord
from discord.ext import commands
import os

# Intents einstellen
intents = discord.Intents.default()
intents.message_content = True

# Bot erstellen
bot = commands.Bot(command_prefix="!", intents=intents)

# Event: Wenn der Bot bereit ist
@bot.event
async def on_ready():
    print(f"✅ Bot ist online! Eingeloggt als {bot.user}")

# Einfacher Command
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

# Bot starten
TOKEN = os.environ.get("TOKEN")  # Token kommt aus den Railway Environment Variables
bot.run(TOKEN)
