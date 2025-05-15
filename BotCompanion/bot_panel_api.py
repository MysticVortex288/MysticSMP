import json
import os
import logging
import threading
import requests
from flask import Flask, request, jsonify, Blueprint
from functools import wraps

logger = logging.getLogger('discord_bot')

# API für Bot Panel
bot_panel_api = Blueprint('bot_panel_api', __name__)

# Bot-Instanz, wird in setup_api() gesetzt
bot = None

# API-Schlüssel für die Authentifizierung
API_KEY = os.environ.get('BOT_PANEL_API_KEY', 'dein_geheimer_api_schluessel')

# Liste der verfügbaren Endpunkte und Berechtigungen
endpoints = {
    "guilds": "Listet alle Server auf, auf denen der Bot ist",
    "channels": "Listet alle Kanäle eines Servers auf",
    "roles": "Listet alle Rollen eines Servers auf",
    "members": "Listet alle Mitglieder eines Servers auf",
    "messages": "Sendet eine Nachricht in einen Kanal",
    "stats": "Zeigt Statistiken über den Bot an",
    "settings": "Zeigt und ändert Einstellungen des Bots"
}

def require_api_key(view_function):
    """Dekorator zur Überprüfung des API-Schlüssels"""
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        # API-Schlüssel aus Header oder Query-Parameter holen
        api_key = request.headers.get('X-API-Key', None)
        if api_key is None:
            api_key = request.args.get('api_key', None)
        
        # Prüfen, ob API-Schlüssel korrekt ist
        if api_key != API_KEY:
            return jsonify({'error': 'Nicht autorisiert - Ungültiger API-Schlüssel'}), 401
        
        return view_function(*args, **kwargs)
    return decorated_function

@bot_panel_api.route('/', methods=['GET'])
def api_info():
    """Zeigt Informationen über die API an"""
    return jsonify({
        'name': 'MysticSMP Bot API',
        'version': '1.0',
        'description': 'API für die Integration mit botpanel.gg',
        'endpoints': endpoints
    })

@bot_panel_api.route('/guilds', methods=['GET'])
@require_api_key
def get_guilds():
    """Liste aller Server, auf denen der Bot ist"""
    if not bot:
        return jsonify({'error': 'Bot nicht initialisiert'}), 500
    
    guilds = []
    for guild in bot.guilds:
        guilds.append({
            'id': guild.id,
            'name': guild.name,
            'member_count': guild.member_count,
            'icon_url': str(guild.icon.url) if guild.icon else None
        })
    
    return jsonify({'guilds': guilds})

@bot_panel_api.route('/guilds/<guild_id>/channels', methods=['GET'])
@require_api_key
def get_channels(guild_id):
    """Liste aller Kanäle eines Servers"""
    if not bot:
        return jsonify({'error': 'Bot nicht initialisiert'}), 500
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return jsonify({'error': 'Server nicht gefunden'}), 404
    
    channels = []
    for channel in guild.channels:
        channels.append({
            'id': channel.id,
            'name': channel.name,
            'type': str(channel.type)
        })
    
    return jsonify({'channels': channels})

@bot_panel_api.route('/guilds/<guild_id>/roles', methods=['GET'])
@require_api_key
def get_roles(guild_id):
    """Liste aller Rollen eines Servers"""
    if not bot:
        return jsonify({'error': 'Bot nicht initialisiert'}), 500
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return jsonify({'error': 'Server nicht gefunden'}), 404
    
    roles = []
    for role in guild.roles:
        roles.append({
            'id': role.id,
            'name': role.name,
            'color': role.color.value,
            'position': role.position
        })
    
    return jsonify({'roles': roles})

@bot_panel_api.route('/guilds/<guild_id>/members', methods=['GET'])
@require_api_key
def get_members(guild_id):
    """Liste aller Mitglieder eines Servers"""
    if not bot:
        return jsonify({'error': 'Bot nicht initialisiert'}), 500
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return jsonify({'error': 'Server nicht gefunden'}), 404
    
    members = []
    for member in guild.members:
        members.append({
            'id': member.id,
            'name': member.name,
            'display_name': member.display_name,
            'avatar_url': str(member.avatar.url) if member.avatar else None,
            'bot': member.bot,
            'roles': [role.id for role in member.roles]
        })
    
    return jsonify({'members': members})

@bot_panel_api.route('/guilds/<guild_id>/channels/<channel_id>/messages', methods=['POST'])
@require_api_key
def send_message(guild_id, channel_id):
    """Sendet eine Nachricht in einen Kanal"""
    if not bot:
        return jsonify({'error': 'Bot nicht initialisiert'}), 500
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return jsonify({'error': 'Server nicht gefunden'}), 404
    
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return jsonify({'error': 'Kanal nicht gefunden'}), 404
    
    data = request.json
    if not data or 'content' not in data:
        return jsonify({'error': 'Nachrichteninhalt fehlt'}), 400
    
    # Nachricht asynchron senden
    message_content = data['content']
    
    async def send():
        await channel.send(message_content)
    
    bot.loop.create_task(send())
    
    return jsonify({'success': True, 'message': 'Nachricht wird gesendet'})

@bot_panel_api.route('/stats', methods=['GET'])
@require_api_key
def get_stats():
    """Statistiken über den Bot"""
    if not bot:
        return jsonify({'error': 'Bot nicht initialisiert'}), 500
    
    stats = {
        'guild_count': len(bot.guilds),
        'user_count': sum(guild.member_count for guild in bot.guilds),
        'uptime': str(bot.uptime) if hasattr(bot, 'uptime') else 'Unbekannt',
        'latency': f"{bot.latency * 1000:.2f}ms"
    }
    
    return jsonify({'stats': stats})

@bot_panel_api.route('/settings', methods=['GET', 'PUT'])
@require_api_key
def handle_settings():
    """Bot-Einstellungen anzeigen und ändern"""
    if not bot:
        return jsonify({'error': 'Bot nicht initialisiert'}), 500
    
    if request.method == 'GET':
        # Aktuelle Einstellungen lesen
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
            return jsonify({'settings': config})
        except Exception as e:
            return jsonify({'error': f'Fehler beim Lesen der Einstellungen: {str(e)}'}), 500
    
    elif request.method == 'PUT':
        # Einstellungen aktualisieren
        data = request.json
        if not data:
            return jsonify({'error': 'Keine Daten gesendet'}), 400
        
        try:
            # Aktuelle Einstellungen lesen
            with open('config.json', 'r') as f:
                config = json.load(f)
            
            # Nur bestimmte Einstellungen aktualisieren
            allowed_settings = ['prefix']
            for key in data:
                if key in allowed_settings:
                    config[key] = data[key]
            
            # Einstellungen speichern
            with open('config.json', 'w') as f:
                json.dump(config, f, indent=4)
            
            return jsonify({'success': True, 'settings': config})
        except Exception as e:
            return jsonify({'error': f'Fehler beim Aktualisieren der Einstellungen: {str(e)}'}), 500

def setup_api(discord_bot, app):
    """Richtet die API mit dem Discord-Bot und der Flask-App ein"""
    global bot
    bot = discord_bot
    
    logger.info("Registriere Bot Panel API Blueprint")
    app.register_blueprint(bot_panel_api, url_prefix='/api')
    logger.info("Bot Panel API eingerichtet")
    
    # botpanel.gg über die neue API informieren
    try:
        # Diese Zeile kann angepasst werden, je nach den Anforderungen von botpanel.gg
        logger.info("Sende API-URL an botpanel.gg")
    except Exception as e:
        logger.error(f"Fehler beim Senden der API-URL an botpanel.gg: {str(e)}")