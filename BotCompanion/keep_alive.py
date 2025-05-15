from flask import Flask, jsonify
from threading import Thread
import logging

# Initialisiere die Flask-App
app = Flask(__name__)
logger = logging.getLogger('discord_bot')

# Discord-Bot Instanz
bot_instance = None

@app.route('/')
def home():
    """Basisendpunkt, der anzeigt, dass der Bot läuft"""
    return "Bot is running!"

@app.route('/status')
def status():
    """Status-Endpunkt für einfache Überprüfungen"""
    if bot_instance:
        status_data = {
            "online": True,
            "guilds": len(bot_instance.guilds),
            "latency": f"{bot_instance.latency * 1000:.2f}ms"
        }
    else:
        status_data = {
            "online": True,
            "message": "Bot wurde noch nicht initialisiert"
        }
    return jsonify(status_data)

def run():
    """Startet den Flask-Server"""
    app.run(host='0.0.0.0', port=8080)

def set_bot(bot):
    """Setzt die Bot-Instanz für API-Zugriff"""
    global bot_instance
    bot_instance = bot
    # Jetzt können wir die Bot Panel API initialisieren
    from bot_panel_api import setup_api
    setup_api(bot, app)
    logger.info("Bot API initialisiert")

def keep_alive(bot=None):
    """
    Startet einen Flask-Server in einem separaten Thread, um den Bot am Laufen zu halten.
    
    Args:
        bot: Die Discord-Bot-Instanz für API-Zugriff (optional)
    """
    if bot:
        set_bot(bot)
    
    t = Thread(target=run)
    t.daemon = True  # Thread wird beendet, wenn das Hauptprogramm endet
    t.start()
    logger.info("Web-Server gestartet auf Port 8080")