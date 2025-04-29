import discord
from discord.ext import commands
import os

# Intents einstellen
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # Für Member-Events wie on_member_join

# Bot erstellen
bot = commands.Bot(command_prefix="!", intents=intents)

# Event: Wenn der Bot bereit ist
@bot.event
async def on_ready():
    print(f"✅ Bot ist online! Eingeloggt als {bot.user}")

    # Cogs laden
    try:
        await bot.load_extension("invite-tracker")
        print("✅ invite-tracker geladen")
    except Exception as e:
        print(f"❌ Fehler bei invite-tracker: {e}")

    try:
        await bot.load_extension("level")
        print("✅ level geladen")
    except Exception as e:
        print(f"❌ Fehler bei level: {e}")

    try:
        await bot.load_extension("help")
        print("✅ help geladen")
    except Exception as e:
        print(f"❌ Fehler bei help: {e}")



@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

# Bot starten
TOKEN = os.environ.get("DISCORD_TOKEN")  # Token kommt aus den Railway Environment Variables
bot.run(TOKEN)
