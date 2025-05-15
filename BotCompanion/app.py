import os
import json
from datetime import datetime, timedelta
import secrets
import requests

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from requests_oauthlib import OAuth2Session


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# Flask-App erstellen
# Discord OAuth2 Konfiguration
DISCORD_CLIENT_ID = os.environ['DISCORD_CLIENT_ID']
DISCORD_CLIENT_SECRET = os.environ['DISCORD_CLIENT_SECRET']
DISCORD_REDIRECT_URI = os.environ.get('DISCORD_REDIRECT_URI', 'https://workspace.sukhjitmultani2.repl.co/callback')
DISCORD_API_BASE_URL = 'https://discord.com/api'
DISCORD_AUTHORIZATION_BASE_URL = DISCORD_API_BASE_URL + '/oauth2/authorize'
DISCORD_TOKEN_URL = DISCORD_API_BASE_URL + '/oauth2/token'

# Flask-App erstellen
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback_secret_key_for_dev")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Für HTTPS-URLs
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Datenbankverbindung konfigurieren
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Debug-Route zum Testen
@app.route('/debug')
def debug():
    return "Debug-Route aktiv! Die App funktioniert."

# Login-Manager initialisieren
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # type: ignore
login_manager.login_message = 'Bitte melde dich an, um diese Seite zu sehen.'


# Benutzermodell für die Datenbank
class User(UserMixin, db.Model):
    __tablename__ = 'dashboard_users'  # Expliziter Tabellenname um Konflikte zu vermeiden
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    discord_id = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=True)
    avatar = db.Column(db.String(255), nullable=True)  # URL zum Discord-Avatar
    is_admin = db.Column(db.Boolean, default=False)
    access_token = db.Column(db.String(255), nullable=True)
    refresh_token = db.Column(db.String(255), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Type overrides für LSP, damit User-Klasse mit UserMixin genutzt werden kann
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return f'<User {self.username}>'


# Hilfsfunktionen für den Zugriff auf JSON-Konfigurationsdateien
def load_json_config(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json_config(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Helper-Funktionen für Discord OAuth
def token_updater(token):
    if current_user.is_authenticated:
        current_user.access_token = token['access_token']
        current_user.refresh_token = token['refresh_token']
        current_user.token_expiry = datetime.now() + timedelta(seconds=token['expires_in'])
        db.session.commit()

def make_discord_session(token=None, state=None, scope=None):
    return OAuth2Session(
        client_id=DISCORD_CLIENT_ID,
        token=token,
        state=state,
        scope=scope,
        redirect_uri=DISCORD_REDIRECT_URI,
        auto_refresh_kwargs={
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
        },
        auto_refresh_url=DISCORD_TOKEN_URL,
        token_updater=token_updater
    )

def get_user_guilds():
    """
    Holt die Serverinformationen für den aktuellen Benutzer
    """
    if not current_user.is_authenticated or not current_user.access_token:
        return []

    try:
        discord = make_discord_session(token={
            'access_token': current_user.access_token,
            'refresh_token': current_user.refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600  # Fixwert für token_type und expires_in
        })

        response = discord.get(f"{DISCORD_API_BASE_URL}/users/@me/guilds")

        # Verarbeite nur Guilds, auf denen der Benutzer Administratorrechte hat
        if response.status_code == 200:
            guilds = response.json()
            # Filtere Guilds, auf denen der Benutzer Admin-Rechte hat (Bit 0x8 für Admin)
            admin_guilds = [g for g in guilds if (int(g['permissions']) & 0x8) == 0x8]
            return admin_guilds
        return []
    except Exception as e:
        print(f"Fehler beim Abrufen der Guilds: {e}")
        return []

def get_bot_guilds():
    """
    Holt die Liste aller Server, auf denen der Bot ist
    """
    bot_guilds_data = []
    try:
        # Wir verwenden die vorhandene Konfigurationsdatei, um die Server zu identifizieren
        # Dies kann durch eine direkte API-Abfrage an den Bot ersetzt werden
        config_files = [
            'guild_languages.json', 'server_stats.json', 'welcome_settings.json',
            'self_roles.json', 'tickets.json', 'temp_voice.json',
            'counting.json', 'verification.json', 'content_announcer.json',
            'moderation.json', 'economy.json'
        ]

        guild_ids = set()

        for file in config_files:
            try:
                config = load_json_config(file)
                # Verarbeite je nach Dateistruktur
                if isinstance(config, dict):
                    # Extrahiere Guild-IDs aus Schlüsseln oder Werten
                    for k, v in config.items():
                        if isinstance(k, str) and k.isdigit():
                            guild_ids.add(k)
                        if isinstance(v, dict) and 'guild_id' in v:
                            guild_ids.add(str(v['guild_id']))
            except Exception:
                pass

        # Konvertiere zu einer Liste von Wörterbüchern für Konsistenz mit Discord API
        bot_guilds_data = [{'id': guild_id} for guild_id in guild_ids]

    except Exception as e:
        print(f"Fehler beim Abrufen der Bot-Guilds: {e}")

    return bot_guilds_data

# Routen
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/server_selection')
@login_required
def server_selection():
    # Hole die Server des Benutzers
    user_guilds = get_user_guilds()
    # Hole die Server, auf denen der Bot aktiv ist
    bot_guilds = get_bot_guilds()

    # Identifiziere, welche Server des Benutzers den Bot bereits haben
    bot_guild_ids = [g['id'] for g in bot_guilds]

    # Teile die Server in zwei Kategorien auf: mit Bot und ohne Bot
    guilds_with_bot = []
    guilds_without_bot = []

    for guild in user_guilds:
        if guild['id'] in bot_guild_ids:
            guilds_with_bot.append(guild)
        else:
            guilds_without_bot.append(guild)

    # Generiere eine Bot-Einladungs-URL
    bot_invite_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&permissions=8&scope=bot%20applications.commands"

    return render_template('server_selection.html', 
                          guilds_with_bot=guilds_with_bot, 
                          guilds_without_bot=guilds_without_bot,
                          bot_invite_url=bot_invite_url)


@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    # Discord OAuth2 URL direkt generieren (robustere Methode)
    import urllib.parse
    client_id = os.environ['DISCORD_CLIENT_ID']
    redirect_uri = os.environ.get('DISCORD_REDIRECT_URI', 'https://workspace.sukhjitmultani2.repl.co/callback')
    oauth_url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&redirect_uri={urllib.parse.quote(redirect_uri)}&response_type=code&scope=identify%20email%20guilds"

    print(f"Login-Prozess gestartet: Direkte Autorisierungs-URL: {oauth_url}")
    return redirect(oauth_url)


@app.route('/discord_callback')
@app.route('/callback')
def callback():
    print(f"Callback aufgerufen mit URL: {request.url}")

    if current_user.is_authenticated:
        return redirect(url_for('server_selection'))

    if request.args.get('error'):
        error_msg = request.args.get('error')
        flash(f"Fehler: {error_msg}", 'danger')
        return redirect(url_for('index'))

    if request.args.get('code') is None:
        print("Kein Code in der Anfrage gefunden")
        flash("Keine Autorisierungsdaten von Discord erhalten.", 'danger')
        return redirect(url_for('index'))

    # Discord Token direkt erhalten
    try:
        code = request.args.get('code')
        print(f"Autorisierungscode erhalten: {code}")

        # Direkte Token-Anfrage
        token_data = {
            'client_id': DISCORD_CLIENT_ID,
            'client_secret': DISCORD_CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': DISCORD_REDIRECT_URI
        }

        print(f"Token-Anfrage mit Daten: {token_data}")

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        r = requests.post(DISCORD_TOKEN_URL, data=token_data, headers=headers)
        print(f"Token-Antwort-Status: {r.status_code}")

        if r.status_code != 200:
            print(f"Fehler bei Token-Anfrage: {r.text}")
            flash('Fehler bei der Discord-Anmeldung. Bitte versuche es erneut.', 'danger')
            return redirect(url_for('index'))

        token = r.json()

        # Benutzerinfos von Discord API abrufen
        headers = {
            'Authorization': f"Bearer {token['access_token']}"
        }
        user_response = requests.get(f"{DISCORD_API_BASE_URL}/users/@me", headers=headers)
        print(f"Benutzerinfo-Antwort-Status: {user_response.status_code}")

        if user_response.status_code != 200:
            print(f"Fehler bei Benutzerinfo-Anfrage: {user_response.text}")
            flash('Fehler beim Abrufen der Benutzerinformationen. Bitte versuche es erneut.', 'danger')
            return redirect(url_for('index'))

        discord_user = user_response.json()
        discord_id = discord_user.get('id')

        # Nach existierendem Benutzer suchen
        user = User.query.filter_by(discord_id=discord_id).first()

        # Neuen Benutzer erstellen, wenn nicht gefunden
        if not user:
            user = User(
                username=discord_user.get('username'),
                discord_id=discord_id,
                email=discord_user.get('email'),
                avatar=f"https://cdn.discordapp.com/avatars/{discord_id}/{discord_user.get('avatar')}.png" if discord_user.get('avatar') else None,
                access_token=token.get('access_token'),
                refresh_token=token.get('refresh_token'),
                token_expiry=datetime.now() + timedelta(seconds=token.get('expires_in', 0))
            )

            # Den ersten Benutzer zum Administrator machen
            if User.query.count() == 0:
                user.is_admin = True

            db.session.add(user)
            db.session.commit()
        else:
            # Benutzerinformationen aktualisieren
            user.username = discord_user.get('username')
            user.email = discord_user.get('email')
            user.avatar = f"https://cdn.discordapp.com/avatars/{discord_id}/{discord_user.get('avatar')}.png" if discord_user.get('avatar') else None
            user.access_token = token.get('access_token')
            user.refresh_token = token.get('refresh_token')
            user.token_expiry = datetime.now() + timedelta(seconds=token.get('expires_in', 0))
            db.session.commit()

        # Benutzer einloggen und zur Serverauswahl weiterleiten
        login_user(user)
        flash('Erfolgreich mit Discord angemeldet!', 'success')
        return redirect(url_for('server_selection'))
    except Exception as e:
        print(f"Fehler bei der Authentifizierung: {str(e)}")
        flash('Ein Fehler ist aufgetreten. Bitte versuche es erneut.', 'danger')
        return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('server_selection'))

@app.route('/dashboard/<guild_id>')
@login_required
def guild_dashboard(guild_id):
    # Hole die Server des Benutzers
    user_guilds = get_user_guilds()
    user_guild_ids = [g['id'] for g in user_guilds]

    # Überprüfe, ob der Benutzer Zugriff auf diesen Server hat
    if guild_id not in user_guild_ids:
        flash('Du hast keinen Zugriff auf diesen Server', 'danger')
        return redirect(url_for('server_selection'))

    # Hole den aktuellen Server
    guild = next((g for g in user_guilds if g['id'] == guild_id), None)

    # Hole Bot-Konfiguration für diesen Server
    server_config = {}
    config_files = {
        'economy': 'economy.json',
        'levels': 'levels.json',
        'welcome': 'welcome_settings.json',
        'tickets': 'tickets.json',
        'counting': 'counting.json',
        'temp_voice': 'temp_voice.json',
        'verification': 'verification.json',
        'content_announcer': 'content_announcer.json'
    }

    for module, file in config_files.items():
        config = load_json_config(file)
        # Prüfe, ob dieser Server eine Konfiguration in der Datei hat
        if isinstance(config, dict):
            if guild_id in config:
                server_config[module] = True
            else:
                for key, value in config.items():
                    if isinstance(value, dict) and value.get('guild_id') == int(guild_id):
                        server_config[module] = True
                        break
                else:
                    server_config[module] = False

    return render_template('guild_dashboard.html', guild=guild, server_config=server_config)


@app.route('/economy')
@login_required
def economy():
    economy_settings = load_json_config('economy.json')
    return render_template('economy.html', settings=economy_settings)


@app.route('/economy/update', methods=['POST'])
@login_required
def update_economy():
    if not current_user.is_admin:
        flash('Nur Administratoren können diese Einstellungen ändern', 'danger')
        return redirect(url_for('economy'))

    settings_key = request.form.get('setting')
    new_value = request.form.get('value')

    if not settings_key or not new_value:
        flash('Ungültige Eingabe', 'danger')
        return redirect(url_for('economy'))

    economy_settings = load_json_config('economy.json')

    # Wertvalidierung basierend auf Einstellungstyp
    if settings_key.endswith('_chance') or settings_key.endswith('_percent'):
        try:
            new_value = float(new_value)
            if new_value < 0 or new_value > 1:
                flash('Prozentsatz muss zwischen 0 und 1 liegen', 'danger')
                return redirect(url_for('economy'))
        except ValueError:
            flash('Ungültiger Wert für Prozentsatz', 'danger')
            return redirect(url_for('economy'))
    elif settings_key.endswith('_cooldown'):
        try:
            new_value = int(new_value)
            if new_value < 0:
                flash('Cooldown kann nicht negativ sein', 'danger')
                return redirect(url_for('economy'))
        except ValueError:
            flash('Ungültiger Wert für Cooldown', 'danger')
            return redirect(url_for('economy'))
    else:
        try:
            new_value = int(new_value)
        except ValueError:
            try:
                new_value = float(new_value)
            except ValueError:
                flash('Ungültiger Wert', 'danger')
                return redirect(url_for('economy'))

    # Update der Einstellungen
    economy_settings[settings_key] = new_value
    save_json_config('economy.json', economy_settings)

    flash(f'Einstellung {settings_key} wurde aktualisiert', 'success')
    return redirect(url_for('economy'))


@app.route('/welcome')
@login_required
def welcome():
    guild_id = request.args.get('guild_id')

    # Wenn keine Guild-ID angegeben ist, zurück zur Server-Auswahl
    if not guild_id:
        flash('Bitte wähle zuerst einen Server aus', 'warning')
        return redirect(url_for('server_selection'))

    # Überprüfe, ob der Benutzer Zugriff auf diesen Server hat
    user_guilds = get_user_guilds()
    user_guild_ids = [g['id'] for g in user_guilds]

    if guild_id not in user_guild_ids:
        flash('Du hast keinen Zugriff auf diesen Server', 'danger')
        return redirect(url_for('server_selection'))

    # Lade die Welcome-Einstellungen
    welcome_settings = load_json_config('welcome_settings.json')

    # Wenn keine Einstellungen für diesen Server vorhanden sind, erstelle sie
    if guild_id not in welcome_settings:
        welcome_settings[guild_id] = {
            'enabled': False,
            'channel_id': None,
            'message': 'Willkommen auf dem Server, {member.mention}!',
            'image_enabled': False,
            'background_url': '',
            'welcome_text': 'Willkommen auf dem Server!',
            'text_color': '#ffffff',
            'font_size': 40
        }
        save_json_config('welcome_settings.json', welcome_settings)

    # Hole den aktuellen Server
    guild = next((g for g in user_guilds if g['id'] == guild_id), None)

    return render_template('welcome.html', settings=welcome_settings[guild_id], guild=guild)


@app.route('/welcome/update', methods=['POST'])
@login_required
def welcome_update():
    guild_id = request.args.get('guild_id')

    # Wenn keine Guild-ID angegeben ist, zurück zur Server-Auswahl
    if not guild_id:
        flash('Bitte wähle zuerst einen Server aus', 'warning')
        return redirect(url_for('server_selection'))

    # Überprüfe, ob der Benutzer Zugriff auf diesen Server hat
    user_guilds = get_user_guilds()
    user_guild_ids = [g['id'] for g in user_guilds]

    if guild_id not in user_guild_ids:
        flash('Du hast keinen Zugriff auf diesen Server', 'danger')
        return redirect(url_for('server_selection'))

    # Lade die Welcome-Einstellungen
    welcome_settings = load_json_config('welcome_settings.json')

    # Wenn keine Einstellungen für diesen Server vorhanden sind, erstelle sie
    if guild_id not in welcome_settings:
        welcome_settings[guild_id] = {
            'enabled': False,
            'channel_id': None,
            'message': 'Willkommen auf dem Server, {member.mention}!',
            'image_enabled': False,
            'background_url': '',
            'welcome_text': 'Willkommen auf dem Server!',
            'text_color': '#ffffff',
            'font_size': 40
        }

    # Update der Einstellungen basierend auf dem Formular
    setting_type = request.form.get('setting_type')

    if setting_type == 'enabled':
        welcome_settings[guild_id]['enabled'] = 'enable_welcome' in request.form
    elif setting_type == 'channel_id':
        welcome_settings[guild_id]['channel_id'] = request.form.get('welcome_channel')
    elif setting_type == 'message':
        welcome_settings[guild_id]['message'] = request.form.get('welcome_message')
    elif setting_type == 'image_enabled':
        welcome_settings[guild_id]['image_enabled'] = 'enable_image' in request.form
    elif setting_type == 'background_url':
        welcome_settings[guild_id]['background_url'] = request.form.get('background_url')
    elif setting_type == 'welcome_text':
        welcome_settings[guild_id]['welcome_text'] = request.form.get('welcome_text')
    elif setting_type == 'text_color':
        welcome_settings[guild_id]['text_color'] = request.form.get('text_color')
    elif setting_type == 'font_size':
        try:
            font_size = int(request.form.get('font_size', 40))
            if 20 <= font_size <= 100:
                welcome_settings[guild_id]['font_size'] = font_size
        except ValueError:
            pass

    # Speichern der aktualisierten Einstellungen
    save_json_config('welcome_settings.json', welcome_settings)

    flash(f'Willkommenseinstellungen wurden aktualisiert', 'success')
    return redirect(url_for('welcome', guild_id=guild_id))


@app.route('/invite_tracker')
@login_required
def invite_tracker():
    invite_settings = load_json_config('invite_tracker.json')
    return render_template('invite_tracker.html', settings=invite_settings)


@app.route('/levels')
@login_required
def levels():
    levels_settings = load_json_config('levels.json')
    return render_template('levels.html', settings=levels_settings)


@app.route('/tickets')
@login_required
def tickets():
    tickets_settings = load_json_config('tickets.json')
    return render_template('tickets.html', settings=tickets_settings)


@app.route('/counting')
@login_required
def counting():
    counting_settings = load_json_config('counting.json')
    return render_template('counting.html', settings=counting_settings)


@app.route('/temp_voice')
@login_required
def temp_voice():
    temp_voice_settings = load_json_config('temp_voice.json')
    return render_template('temp_voice.html', settings=temp_voice_settings)


@app.route('/verification')
@login_required
def verification():
    verification_settings = load_json_config('verification.json')
    return render_template('verification.html', settings=verification_settings)


@app.route('/content_announcer')
@login_required
def content_announcer():
    content_settings = load_json_config('content_announcer.json')
    return render_template('content_announcer.html', settings=content_settings)


@app.route('/self_roles')
@login_required
def self_roles():
    roles_settings = load_json_config('self_roles.json')
    return render_template('self_roles.html', settings=roles_settings)


@app.route('/bot_assistant')
@login_required
def bot_assistant():
    assistant_settings = load_json_config('bot_assistant.json')
    return render_template('bot_assistant.html', settings=assistant_settings)


@app.route('/server_stats')
@login_required
def server_stats():
    stats_settings = load_json_config('server_stats.json')
    return render_template('server_stats.html', settings=stats_settings)


@app.route('/language')
@login_required
def language():
    guild_languages = load_json_config('guild_languages.json')
    user_languages = load_json_config('user_languages.json')
    translations = load_json_config('translations.json')
    return render_template('language.html', guild_languages=guild_languages, 
                           user_languages=user_languages, translations=translations)


@app.route('/channel_locker')
@login_required
def channel_locker():
    locker_settings = load_json_config('locked_channels.json')
    return render_template('channel_locker.html', settings=locker_settings)


@app.route('/emoji_stealer')
@login_required
def emoji_stealer():
    return render_template('emoji_stealer.html')


@app.route('/captcha')
@login_required
def captcha():
    captcha_settings = load_json_config('captcha_settings.json')
    return render_template('captcha.html', settings=captcha_settings)


@app.route('/moderation')
@login_required
def moderation():
    moderation_settings = load_json_config('moderation.json')
    return render_template('moderation.html', settings=moderation_settings)


@app.route('/api/bot_status')
def api_bot_status():
    # Hier könnten wir den Bot-Status abfragen, für jetzt nur ein Beispiel
    return jsonify({
        'status': 'online',
        'uptime': '3d 4h 12m',
        'guilds': 1,
        'commands': 80
    })


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


@app.route('/downloads')
def downloads():
    """Zeigt die Download-Seite an"""
    return render_template('download_textual.html')


@app.route('/download/mybot')
def download_mybot():
    """Stellt die vollständige ZIP-Datei zum Download bereit"""
    return send_file('mybot.zip', as_attachment=True, download_name='discordbot.zip')


@app.route('/download/project')
def download_project():
    """Stellt die kompakte ZIP-Datei zum Download bereit"""
    return send_file('projekt_backup.zip', as_attachment=True, download_name='discordbot_compact.zip')


@app.route('/download_file/anleitung')
def download_anleitung():
    """Stellt die Anleitung als Datei zum Download bereit"""
    return send_file('discord_bot_anleitung.md', as_attachment=True)


@app.route('/textdownload')
def text_download_info():
    """Zeigt eine einfache Textseite mit Download-Informationen an"""
    with open('download_info.txt', 'r') as file:
        content = file.read()
    return render_template('text_download.html', content=content)


# Datenbank erstellen
@app.route('/test-database')
def test_database():
    try:
        with app.app_context():
            db.create_all()
            return "Datenbankverbindung erfolgreich hergestellt!"
    except Exception as e:
        return f"Datenbankfehler: {str(e)}"

with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)