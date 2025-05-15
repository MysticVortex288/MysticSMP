import os
import asyncio
from app import app

# Hauptfunktion für die Ausführung des Bots
async def main():
    from bot import initialize_bot
    # Bot initialisieren
    bot = await initialize_bot()
    
    # API-Token aus Umgebungsvariable holen
    TOKEN = os.environ.get('DISCORD_TOKEN')
    if not TOKEN:
        print("Fehler: DISCORD_TOKEN Umgebungsvariable nicht gefunden")
        return
    
    try:
        # Bot starten
        await bot.start(TOKEN)
    except KeyboardInterrupt:
        await bot.close()

# Starte nur den Bot, wenn das Skript direkt ausgeführt wird
if __name__ == "__main__":
    # Bot starten
    asyncio.run(main())