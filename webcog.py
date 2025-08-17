from discord.ext import commands
from flask import Flask, redirect, request, session, url_for, jsonify
import threading
import os
import requests
import json

# Discord OAuth2 Daten
CLIENT_ID = "1397289097009168454"
CLIENT_SECRET = "M3cnDNfM88-HIp138E20_IXF9-1L3lz5"
REDIRECT_URI = "http://fi1.bot-hosting.net:5379/discord-callback"
SCOPE = "identify guilds"
Token = os.getenv("Token")

# Cog Management
COG_SETTINGS_FILE = "data/cog_settings.json"
AUTOROLE_FILE = "data/autorole.json"

def ensure_data_dir():
    if not os.path.exists("data"):
        os.makedirs("data")

def load_cog_settings():
    ensure_data_dir()
    if os.path.exists(COG_SETTINGS_FILE):
        with open(COG_SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cog_settings(data):
    ensure_data_dir()
    with open(COG_SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_autorole_settings():
    ensure_data_dir()
    if os.path.exists(AUTOROLE_FILE):
        with open(AUTOROLE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_autorole_settings(data):
    ensure_data_dir()
    with open(AUTOROLE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Available Cogs with enhanced styling information
AVAILABLE_COGS = {
    "AutoMod": {
        "name": "AutoMod",
        "description": "Advanced automatic moderation with intelligent word filtering, spam protection, and rule enforcement",
        "icon": "🛡️",
        "module": "automod",
        "color": "#e74c3c",
        "category": "Moderation"
    },
    "AutoRole": {
        "name": "AutoRole", 
        "description": "Automatically assign custom roles to new members when they join your server",
        "icon": "🎭",
        "module": "autorole",
        "color": "#9b59b6",
        "category": "Management"
    },
    "CountingGame": {
        "name": "Counting Game",
        "description": "Interactive counting game with leaderboards and achievements for community engagement", 
        "icon": "🔢",
        "module": "counting",
        "color": "#f39c12",
        "category": "Fun"
    },
    "DM": {
        "name": "DM System",
        "description": "Personalized welcome DMs and powerful mass messaging features for announcements",
        "icon": "💌",
        "module": "dm",
        "color": "#e91e63",
        "category": "Communication"
    },
    "EmbedColor": {
        "name": "Embed Colors",
        "description": "Custom embed colors and styling options for premium users and server branding",
        "icon": "🎨", 
        "module": "embedcolor",
        "color": "#3498db",
        "category": "Customization"
    },
    "Giveaway": {
        "name": "Giveaways",
        "description": "Create and manage engaging server giveaways with automatic winner selection",
        "icon": "🎉",
        "module": "giveaway",
        "color": "#2ecc71",
        "category": "Events"
    },
    "InviteTracker": {
        "name": "Invite Tracker",
        "description": "Comprehensive invite tracking system with detailed analytics and leaderboards",
        "icon": "📊",
        "module": "invitetracker",
        "color": "#1abc9c",
        "category": "Analytics"
    },
    "LevelSystem": {
        "name": "Level System",
        "description": "Engaging XP and leveling system with customizable rewards and role progression",
        "icon": "⭐",
        "module": "levelsystem",
        "color": "#f1c40f",
        "category": "Gamification"
    },
    "Moderation": {
        "name": "Moderation",
        "description": "Complete moderation toolkit with timeout, ban, kick, warn and advanced purge commands",
        "icon": "🔨",
        "module": "moderation",
        "color": "#e74c3c",
        "category": "Moderation"
    },
    "PingRoles": {
        "name": "Ping Roles",
        "description": "Self-assignable roles with beautiful dropdown menus and reaction-based assignment",
        "icon": "🏷️",
        "module": "pingroles",
        "color": "#9b59b6",
        "category": "Management"
    },
    "Embed": {
        "name": "Embed Creator",
        "description": "Professional embed message creator with rich formatting and interactive builders",
        "icon": "📝",
        "module": "embed",
        "color": "#34495e",
        "category": "Tools"
    },
    "SuggestionCog": {
        "name": "Suggestions",
        "description": "Community suggestion system with voting, approval workflow and feedback management",
        "icon": "💡",
        "module": "suggestion",
        "color": "#f39c12",
        "category": "Community"
    },
    "Ticket": {
        "name": "Ticket System",
        "description": "Advanced support ticket system with categories, transcripts and staff management",
        "icon": "🎫",
        "module": "ticket",
        "color": "#3498db",
        "category": "Support"
    },
    "Verification": {
        "name": "Verification",
        "description": "Secure captcha-based member verification system with anti-bot protection",
        "icon": "🔐",
        "module": "verification",
        "color": "#27ae60",
        "category": "Security"
    }
}

class ModwayDashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_webserver()

    def get_cog_status(self, guild_id, cog_name):
        """Get the enabled/disabled status of a cog for a specific guild"""
        settings = load_cog_settings()
        return settings.get(str(guild_id), {}).get(cog_name, True)  # Default enabled

    def set_cog_status(self, guild_id, cog_name, enabled):
        """Set the enabled/disabled status of a cog for a specific guild"""
        settings = load_cog_settings()
        if str(guild_id) not in settings:
            settings[str(guild_id)] = {}
        settings[str(guild_id)][cog_name] = enabled
        save_cog_settings(settings)
    
    def load_automod_settings(self, guild_id):
        """Load AutoMod settings for a specific guild"""
        automod_file = "data/automod.json"
        ensure_data_dir()
        
        if os.path.exists(automod_file):
            with open(automod_file, "r") as f:
                data = json.load(f)
                return data.get(str(guild_id), self.get_default_automod_settings())
        
        return self.get_default_automod_settings()
    
    def save_automod_settings(self, guild_id, settings):
        """Save AutoMod settings for a specific guild"""
        automod_file = "data/automod.json"
        ensure_data_dir()
        
        data = {}
        if os.path.exists(automod_file):
            with open(automod_file, "r") as f:
                data = json.load(f)
        
        data[str(guild_id)] = settings
        
        with open(automod_file, "w") as f:
            json.dump(data, f, indent=4)
    
    def get_default_automod_settings(self):
        """Get default AutoMod settings"""
        return {
            "enabled": True,
            "badwords": [],
            "action": "timeout",
            "antispam": {
                "enabled": False,
                "max_messages": 5,
                "time_window": 8,
                "punishment": "timeout",
                "timeout_duration": 5
            },
            "whitelist_roles": [],
            "whitelist_channels": [],
            "log_channel": None
        }

    def generate_cog_cards(self, guild_id):
        """Generate enhanced HTML cards for all cogs with their status"""
        # Group cogs by category
        categories = {}
        for cog_key, cog_info in AVAILABLE_COGS.items():
            category = cog_info.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append((cog_key, cog_info))
        
        cards_html = ""
        for category, cogs in categories.items():
            cards_html += f"""
            <div class="category-section">
                <div class="category-header">
                    <h3 class="category-title">{category}</h3>
                    <div class="category-divider"></div>
                </div>
                <div class="category-grid">
            """
            
            for cog_key, cog_info in cogs:
                is_enabled = self.get_cog_status(guild_id, cog_key)
                status_class = "enabled" if is_enabled else "disabled"
                status_text = "Enabled" if is_enabled else "Disabled"
                toggle_class = "enabled" if is_enabled else ""
                
                # Add configuration button for AutoMod and AutoRole
                config_button = ""
                if cog_key == "AutoMod" and is_enabled:
                    config_button = f'<a href="/config/automod/{guild_id}" class="config-btn">⚙️ Configure</a>'
                elif cog_key == "AutoRole" and is_enabled:
                    config_button = f'<a href="/config/autorole/{guild_id}" class="config-btn">⚙️ Configure</a>'
                
                cards_html += f"""
                <div class="cog-card {status_class}" style="--cog-color: {cog_info['color']}">
                    <div class="cog-card-inner">
                        <div class="cog-header">
                            <div class="cog-title">
                                <div class="cog-icon">{cog_info['icon']}</div>
                                <div class="cog-info">
                                    <h3 class="cog-name">{cog_info['name']}</h3>
                                    <span class="cog-category">{cog_info['category']}</span>
                                </div>
                            </div>
                            <div class="toggle-container">
                                <div class="toggle-switch {toggle_class}" onclick="toggleCog('{guild_id}', '{cog_key}')">
                                    <div class="toggle-slider"></div>
                                </div>
                            </div>
                        </div>
                        <p class="cog-description">{cog_info['description']}</p>
                        <div class="cog-status">
                            <div class="status-indicator">
                                <div class="status-dot {status_class}"></div>
                                <span class="status-text">{status_text}</span>
                            </div>
                            {config_button}
                        </div>
                    </div>
                    <div class="cog-card-glow"></div>
                </div>
                """
            
            cards_html += """
                </div>
            </div>
            """
        
        return cards_html

    def start_webserver(self):
        app = Flask("ModwayDashboard")
        app.secret_key = os.urandom(24)

        @app.route("/")
        def home():
            user = session.get("user")
            if user:
                username = user["username"]
                discriminator = user["discriminator"]
                avatar = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png" if user['avatar'] else "https://cdn.discordapp.com/embed/avatars/{int(discriminator) % 5}.png"
                login_section = f"""
                    <div class="user-info">
                        <div class="user-details">
                            <img src="{avatar}" class="user-avatar">
                            <div class="user-text">
                                <span class="username">{username}</span>
                                <span class="discriminator">#{discriminator}</span>
                            </div>
                        </div>
                        <div class="user-actions">
                            <a href="/servers" class="action-btn primary">🚀 Manage Servers</a>
                            <a href="/logout" class="action-btn secondary">👋 Logout</a>
                        </div>
                    </div>
                """
            else:
                login_section = '''
                    <div class="login-section">
                        <a href="/discord-login" class="discord-login-btn">
                            <svg class="discord-icon" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
                            </svg>
                            Login with Discord
                        </a>
                    </div>
                '''

            return f"""
            <!DOCTYPE html>
            <html lang="en">
              <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Modway Dashboard | Advanced Discord Bot Management</title>
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <style>
                  :root {{
                    --primary-color: #5865f2;
                    --primary-hover: #4752c4;
                    --secondary-color: #7c3aed;
                    --background-dark: #0d1117;
                    --background-card: #161b22;
                    --text-primary: #ffffff;
                    --text-secondary: #8b949e;
                    --border-color: #30363d;
                    --success-color: #238636;
                    --warning-color: #f85149;
                    --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    --gradient-secondary: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
                    --shadow-xl: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
                  }}
                  
                  * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                  }}
                  
                  body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    background: var(--background-dark);
                    color: var(--text-primary);
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                    position: relative;
                    overflow-x: hidden;
                  }}
                  
                  body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: var(--gradient-primary);
                    opacity: 0.05;
                    z-index: -1;
                  }}
                  
                  .animated-bg {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    z-index: -2;
                    background: radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.3) 0%, transparent 50%),
                                radial-gradient(circle at 80% 20%, rgba(255, 119, 198, 0.3) 0%, transparent 50%),
                                radial-gradient(circle at 40% 80%, rgba(120, 219, 255, 0.3) 0%, transparent 50%);
                    animation: gradientShift 15s ease infinite;
                  }}
                  
                  @keyframes gradientShift {{
                    0%, 100% {{ transform: scale(1) rotate(0deg); opacity: 0.3; }}
                    50% {{ transform: scale(1.1) rotate(180deg); opacity: 0.5; }}
                  }}
                  
                  .user-info {{
                    position: fixed;
                    top: 30px;
                    right: 30px;
                    display: flex;
                    align-items: center;
                    gap: 20px;
                    background: var(--background-card);
                    padding: 15px 25px;
                    border-radius: 20px;
                    border: 1px solid var(--border-color);
                    backdrop-filter: blur(20px);
                    box-shadow: var(--shadow-lg);
                    z-index: 100;
                  }}
                  
                  .user-details {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                  }}
                  
                  .user-avatar {{
                    width: 45px;
                    height: 45px;
                    border-radius: 50%;
                    border: 2px solid var(--primary-color);
                  }}
                  
                  .user-text {{
                    display: flex;
                    flex-direction: column;
                  }}
                  
                  .username {{
                    font-weight: 600;
                    color: var(--text-primary);
                  }}
                  
                  .discriminator {{
                    font-size: 0.85em;
                    color: var(--text-secondary);
                  }}
                  
                  .user-actions {{
                    display: flex;
                    gap: 10px;
                  }}
                  
                  .action-btn {{
                    padding: 10px 18px;
                    border-radius: 12px;
                    text-decoration: none;
                    font-weight: 500;
                    font-size: 0.9em;
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                  }}
                  
                  .action-btn.primary {{
                    background: var(--primary-color);
                    color: white;
                  }}
                  
                  .action-btn.primary:hover {{
                    background: var(--primary-hover);
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(88, 101, 242, 0.4);
                  }}
                  
                  .action-btn.secondary {{
                    background: rgba(255, 255, 255, 0.1);
                    color: var(--text-primary);
                    border: 1px solid var(--border-color);
                  }}
                  
                  .action-btn.secondary:hover {{
                    background: rgba(255, 255, 255, 0.15);
                    transform: translateY(-2px);
                  }}
                  
                  .login-section {{
                    position: fixed;
                    top: 30px;
                    right: 30px;
                    z-index: 100;
                  }}
                  
                  .discord-login-btn {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    background: var(--primary-color);
                    color: white;
                    padding: 15px 25px;
                    border-radius: 16px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 1em;
                    transition: all 0.4s ease;
                    border: none;
                    cursor: pointer;
                    box-shadow: var(--shadow-lg);
                    position: relative;
                    overflow: hidden;
                  }}
                  
                  .discord-login-btn::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: -100%;
                    width: 100%;
                    height: 100%;
                    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                    transition: left 0.6s ease;
                  }}
                  
                  .discord-login-btn:hover::before {{
                    left: 100%;
                  }}
                  
                  .discord-login-btn:hover {{
                    background: var(--primary-hover);
                    transform: translateY(-3px) scale(1.02);
                    box-shadow: 0 20px 40px rgba(88, 101, 242, 0.4);
                  }}
                  
                  .discord-icon {{
                    width: 24px;
                    height: 24px;
                    fill: currentColor;
                  }}
                  
                  .main-card {{
                    background: var(--background-card);
                    border-radius: 30px;
                    padding: 60px;
                    text-align: center;
                    border: 1px solid var(--border-color);
                    backdrop-filter: blur(20px);
                    box-shadow: var(--shadow-xl);
                    max-width: 800px;
                    width: 100%;
                    position: relative;
                    overflow: hidden;
                    animation: cardFloat 6s ease-in-out infinite;
                  }}
                  
                  .main-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: var(--gradient-primary);
                    border-radius: 30px 30px 0 0;
                  }}
                  
                  @keyframes cardFloat {{
                    0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
                    50% {{ transform: translateY(-10px) rotate(0.5deg); }}
                  }}
                  
                  .main-title {{
                    font-size: 4em;
                    font-weight: 700;
                    margin-bottom: 20px;
                    background: var(--gradient-primary);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    line-height: 1.2;
                    animation: titleGlow 3s ease-in-out infinite alternate;
                  }}
                  
                  @keyframes titleGlow {{
                    0% {{ filter: brightness(1); }}
                    100% {{ filter: brightness(1.2); }}
                  }}
                  
                  .main-subtitle {{
                    font-size: 1.4em;
                    color: var(--text-secondary);
                    margin-bottom: 40px;
                    font-weight: 400;
                    line-height: 1.6;
                  }}
                  
                  .features-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-top: 50px;
                  }}
                  
                  .feature-card {{
                    background: rgba(255, 255, 255, 0.03);
                    border: 1px solid var(--border-color);
                    border-radius: 16px;
                    padding: 25px 20px;
                    text-align: center;
                    transition: all 0.3s ease;
                    cursor: pointer;
                  }}
                  
                  .feature-card:hover {{
                    transform: translateY(-8px);
                    background: rgba(255, 255, 255, 0.08);
                    border-color: var(--primary-color);
                    box-shadow: 0 15px 30px rgba(88, 101, 242, 0.2);
                  }}
                  
                  .feature-icon {{
                    font-size: 2.5em;
                    margin-bottom: 15px;
                    display: block;
                  }}
                  
                  .feature-title {{
                    font-size: 1.1em;
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: var(--text-primary);
                  }}
                  
                  .feature-desc {{
                    font-size: 0.9em;
                    color: var(--text-secondary);
                    line-height: 1.4;
                  }}
                  
                  .footer {{
                    position: fixed;
                    bottom: 30px;
                    left: 50%;
                    transform: translateX(-50%);
                    font-size: 0.9em;
                    color: var(--text-secondary);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    background: var(--background-card);
                    padding: 12px 20px;
                    border-radius: 25px;
                    border: 1px solid var(--border-color);
                    backdrop-filter: blur(20px);
                  }}
                  
                  .creator-badge {{
                    background: var(--gradient-secondary);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    font-weight: 600;
                  }}
                  
                  @media (max-width: 768px) {{
                    body {{ padding: 10px; }}
                    .user-info, .login-section {{ 
                      position: static; 
                      margin-bottom: 20px;
                      width: 100%;
                      justify-content: center;
                    }}
                    .main-card {{ 
                      padding: 40px 30px; 
                      margin-top: 20px;
                    }}
                    .main-title {{ font-size: 2.8em; }}
                    .main-subtitle {{ font-size: 1.2em; }}
                    .features-grid {{ grid-template-columns: 1fr; }}
                  }}
                </style>
              </head>
              <body>
                <div class="animated-bg"></div>
                
                {login_section}
                
                <div class="main-card">
                  <h1 class="main-title">Modway Dashboard</h1>
                  <p class="main-subtitle">Advanced Discord bot management with powerful features and intuitive controls</p>
                  
                  <div class="features-grid">
                    <div class="feature-card">
                      <div class="feature-icon">🚀</div>
                      <div class="feature-title">Easy Management</div>
                      <div class="feature-desc">Manage all bot features from one central dashboard</div>
                    </div>
                    <div class="feature-card">
                      <div class="feature-icon">⚡</div>
                      <div class="feature-title">Real-time Updates</div>
                      <div class="feature-desc">Instant configuration changes across all servers</div>
                    </div>
                    <div class="feature-card">
                      <div class="feature-icon">🔒</div>
                      <div class="feature-title">Secure Access</div>
                      <div class="feature-desc">Discord OAuth2 authentication for maximum security</div>
                    </div>
                    <div class="feature-card">
                      <div class="feature-icon">📊</div>
                      <div class="feature-title">Analytics</div>
                      <div class="feature-desc">Comprehensive insights and usage statistics</div>
                    </div>
                  </div>
                </div>
                
                <div class="footer">
                  <span>Crafted with ❤️ by</span>
                  <span class="creator-badge">MysticVortex786</span>
                </div>
              </body>
            </html>
            """

        @app.route("/discord-login")
        def discord_login():
            discord_auth_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={SCOPE}"
            return redirect(discord_auth_url)

        @app.route("/discord-callback")
        def discord_callback():
            code = request.args.get("code")
            if not code:
                return "❌ No code returned from Discord."

            data = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "scope": SCOPE
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
            r.raise_for_status()
            token_data = r.json()
            access_token = token_data["access_token"]

            user_data = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {access_token}"}).json()
            session["user"] = user_data
            session["access_token"] = access_token
            return redirect("/")

        @app.route("/logout")
        def logout():
            session.pop("user", None)
            session.pop("access_token", None)
            return redirect("/")

        @app.route("/servers")
        def servers():
            user = session.get("user")
            if not user:
                return redirect("/discord-login")
            
            access_token = session.get("access_token")
            if not access_token:
                return redirect("/discord-login")
            
            user_guilds_response = requests.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_guilds_response.status_code != 200:
                return "❌ Failed to fetch your servers."
            
            user_guilds = user_guilds_response.json()
            
            bot_guilds_response = requests.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bot {Token}"}
            )
            
            bot_guild_ids = []
            if bot_guilds_response.status_code == 200:
                bot_guild_ids = [guild["id"] for guild in bot_guilds_response.json()]
            
            manageable_guilds = [guild for guild in user_guilds if int(guild["permissions"]) & 0x20]
            
            guild_cards = ""
            for guild in manageable_guilds:
                guild_icon = f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png" if guild['icon'] else "https://cdn.discordapp.com/embed/avatars/0.png"
                
                if guild["id"] in bot_guild_ids:
                    action_btn = f'<a href="/manage/{guild["id"]}" class="action-btn manage">🎛️ Manage Server</a>'
                    status_badge = '<div class="status-badge connected">🟢 Connected</div>'
                else:
                    action_btn = f'<a href="/invite/{guild["id"]}" class="action-btn invite">➕ Add Bot</a>'
                    status_badge = '<div class="status-badge disconnected">⚪ Not Connected</div>'
                
                guild_cards += f"""
                <div class="guild-card">
                    <div class="guild-header">
                        <img src="{guild_icon}" class="guild-icon" loading="lazy">
                        <div class="guild-info">
                            <h3 class="guild-name">{guild['name']}</h3>
                            <p class="guild-id">ID: {guild['id']}</p>
                            {status_badge}
                        </div>
                    </div>
                    <div class="guild-actions">
                        {action_btn}
                    </div>
                    <div class="guild-card-glow"></div>
                </div>
                """
            
            return f"""
            <!DOCTYPE html>
            <html lang="en">
              <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Modway Dashboard - Your Servers</title>
                <link rel="preconnect" href="https://fonts.googleapis.com">
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <style>
                  :root {{
                    --primary-color: #5865f2;
                    --primary-hover: #4752c4;
                    --secondary-color: #7c3aed;
                    --background-dark: #0d1117;
                    --background-card: #161b22;
                    --text-primary: #ffffff;
                    --text-secondary: #8b949e;
                    --border-color: #30363d;
                    --success-color: #238636;
                    --warning-color: #f85149;
                    --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
                  }}
                  
                  * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                  }}
                  
                  body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    background: var(--background-dark);
                    color: var(--text-primary);
                    min-height: 100vh;
                    padding: 20px;
                    position: relative;
                  }}
                  
                  body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: var(--gradient-primary);
                    opacity: 0.05;
                    z-index: -1;
                  }}
                  
                  .header {{
                    text-align: center;
                    margin-bottom: 50px;
                    padding-top: 20px;
                  }}
                  
                  .page-title {{
                    font-size: 3.5em;
                    font-weight: 700;
                    margin-bottom: 15px;
                    background: var(--gradient-primary);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                  }}
                  
                  .page-subtitle {{
                    font-size: 1.2em;
                    color: var(--text-secondary);
                    margin-bottom: 30px;
                  }}
                  
                  .back-btn {{
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    background: var(--background-card);
                    border: 1px solid var(--border-color);
                    padding: 12px 20px;
                    border-radius: 12px;
                    color: var(--text-primary);
                    text-decoration: none;
                    font-weight: 500;
                    transition: all 0.3s ease;
                    backdrop-filter: blur(20px);
                  }}
                  
                  .back-btn:hover {{
                    background: var(--primary-color);
                    border-color: var(--primary-color);
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(88, 101, 242, 0.3);
                  }}
                  
                  .guilds-container {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
                    gap: 25px;
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 0 10px;
                  }}
                  
                  .guild-card {{
                    background: var(--background-card);
                    border: 1px solid var(--border-color);
                    border-radius: 20px;
                    padding: 25px;
                    transition: all 0.4s ease;
                    position: relative;
                    overflow: hidden;
                    backdrop-filter: blur(20px);
                  }}
                  
                  .guild-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 3px;
                    background: var(--gradient-primary);
                    opacity: 0;
                    transition: opacity 0.3s ease;
                  }}
                  
                  .guild-card:hover {{
                    transform: translateY(-8px);
                    border-color: var(--primary-color);
                    box-shadow: var(--shadow-lg);
                  }}
                  
                  .guild-card:hover::before {{
                    opacity: 1;
                  }}
                  
                  .guild-header {{
                    display: flex;
                    align-items: center;
                    gap: 20px;
                    margin-bottom: 20px;
                  }}
                  
                  .guild-icon {{
                    width: 70px;
                    height: 70px;
                    border-radius: 16px;
                    border: 2px solid var(--border-color);
                    transition: all 0.3s ease;
                  }}
                  
                  .guild-card:hover .guild-icon {{
                    border-color: var(--primary-color);
                    transform: scale(1.05);
                  }}
                  
                  .guild-info {{
                    flex: 1;
                  }}
                  
                  .guild-name {{
                    font-size: 1.4em;
                    font-weight: 600;
                    margin-bottom: 5px;
                    color: var(--text-primary);
                  }}
                  
                  .guild-id {{
                    font-size: 0.85em;
                    color: var(--text-secondary);
                    font-family: 'Monaco', monospace;
                    margin-bottom: 8px;
                  }}
                  
                  .status-badge {{
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    padding: 4px 10px;
                    border-radius: 20px;
                    font-size: 0.8em;
                    font-weight: 500;
                  }}
                  
                  .status-badge.connected {{
                    background: rgba(35, 134, 54, 0.2);
                    color: #3fb950;
                    border: 1px solid rgba(35, 134, 54, 0.3);
                  }}
                  
                  .status-badge.disconnected {{
                    background: rgba(139, 148, 158, 0.2);
                    color: var(--text-secondary);
                    border: 1px solid var(--border-color);
                  }}
                  
                  .guild-actions {{
                    display: flex;
                    justify-content: center;
                  }}
                  
                  .action-btn {{
                    padding: 12px 24px;
                    border-radius: 12px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 0.95em;
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                  }}
                  
                  .action-btn.manage {{
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                  }}
                  
                  .action-btn.manage:hover {{
                    transform: translateY(-2px) scale(1.02);
                    box-shadow: 0 10px 25px rgba(240, 147, 251, 0.4);
                  }}
                  
                  .action-btn.invite {{
                    background: var(--success-color);
                    color: white;
                  }}
                  
                  .action-btn.invite:hover {{
                    background: #2ea043;
                    transform: translateY(-2px) scale(1.02);
                    box-shadow: 0 10px 25px rgba(35, 134, 54, 0.4);
                  }}
                  
                  .empty-state {{
                    text-align: center;
                    padding: 80px 20px;
                    color: var(--text-secondary);
                    grid-column: 1 / -1;
                  }}
                  
                  .empty-state-icon {{
                    font-size: 4em;
                    margin-bottom: 20px;
                    opacity: 0.5;
                  }}
                  
                  .empty-state-text {{
                    font-size: 1.2em;
                    font-weight: 500;
                  }}
                  
                  @media (max-width: 768px) {{
                    .guilds-container {{
                      grid-template-columns: 1fr;
                      padding: 0 5px;
                    }}
                    .guild-card {{ padding: 20px; }}
                    .guild-header {{ gap: 15px; }}
                    .guild-icon {{ width: 60px; height: 60px; }}
                    .page-title {{ font-size: 2.5em; }}
                  }}
                </style>
              </head>
              <body>
                <div class="header">
                    <h1 class="page-title">Your Servers</h1>
                    <p class="page-subtitle">Manage your Discord servers and bot configurations</p>
                    <a href="/" class="back-btn">← Back to Dashboard</a>
                </div>
                
                <div class="guilds-container">
                    {guild_cards if guild_cards else '''
                    <div class="empty-state">
                        <div class="empty-state-icon">🏰</div>
                        <div class="empty-state-text">No manageable servers found</div>
                    </div>
                    '''}
                </div>
              </body>
            </html>
            """
        
        @app.route("/invite/<guild_id>")
        def invite_confirm(guild_id):
            user = session.get("user")
            if not user:
                return redirect("/discord-login")
            
            access_token = session.get("access_token")
            if not access_token:
                return redirect("/discord-login")
            
            user_guilds_response = requests.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            guild_info = None
            if user_guilds_response.status_code == 200:
                guilds = user_guilds_response.json()
                guild_info = next((g for g in guilds if g["id"] == guild_id), None)
            
            if not guild_info:
                return "❌ Server not found."
            
            guild_icon = f"https://cdn.discordapp.com/icons/{guild_info['id']}/{guild_info['icon']}.png" if guild_info['icon'] else "https://cdn.discordapp.com/embed/avatars/0.png"
            invite_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&permissions=8&guild_id={guild_id}&response_type=code&redirect_uri={REDIRECT_URI}&scope=bot"
            
            return f"""
            <!DOCTYPE html>
            <html lang="en">
              <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Modway Dashboard - Add Bot</title>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <style>
                  :root {{
                    --primary-color: #5865f2;
                    --primary-hover: #4752c4;
                    --success-color: #238636;
                    --danger-color: #da373d;
                    --background-dark: #0d1117;
                    --background-card: #161b22;
                    --text-primary: #ffffff;
                    --text-secondary: #8b949e;
                    --border-color: #30363d;
                    --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    --shadow-xl: 0 25px 50px -12px rgba(0, 0, 0, 0.6);
                  }}
                  
                  * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                  }}
                  
                  body {{
                    font-family: 'Inter', sans-serif;
                    background: var(--background-dark);
                    color: var(--text-primary);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                    position: relative;
                  }}
                  
                  body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: var(--gradient-primary);
                    opacity: 0.05;
                    z-index: -1;
                  }}
                  
                  .confirm-card {{
                    background: var(--background-card);
                    border: 1px solid var(--border-color);
                    border-radius: 24px;
                    padding: 50px 40px;
                    text-align: center;
                    max-width: 600px;
                    width: 100%;
                    backdrop-filter: blur(20px);
                    box-shadow: var(--shadow-xl);
                    position: relative;
                    overflow: hidden;
                  }}
                  
                  .confirm-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: var(--gradient-primary);
                  }}
                  
                  .server-icon {{
                    width: 120px;
                    height: 120px;
                    border-radius: 20px;
                    border: 3px solid var(--primary-color);
                    margin: 0 auto 25px auto;
                    display: block;
                    transition: all 0.3s ease;
                  }}
                  
                  .server-icon:hover {{
                    transform: scale(1.05);
                    box-shadow: 0 10px 30px rgba(88, 101, 242, 0.3);
                  }}
                  
                  .confirm-title {{
                    font-size: 2.2em;
                    font-weight: 700;
                    margin-bottom: 15px;
                    background: var(--gradient-primary);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                  }}
                  
                  .confirm-subtitle {{
                    font-size: 1.1em;
                    color: var(--text-secondary);
                    margin-bottom: 35px;
                    line-height: 1.5;
                  }}
                  
                  .permissions-box {{
                    background: rgba(88, 101, 242, 0.1);
                    border: 1px solid rgba(88, 101, 242, 0.3);
                    border-radius: 16px;
                    padding: 25px;
                    margin: 30px 0;
                    text-align: left;
                  }}
                  
                  .permissions-title {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-size: 1.2em;
                    font-weight: 600;
                    margin-bottom: 15px;
                    color: var(--primary-color);
                  }}
                  
                  .permissions-list {{
                    list-style: none;
                    padding: 0;
                  }}
                  
                  .permissions-list li {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 8px 0;
                    color: var(--text-secondary);
                    border-bottom: 1px solid var(--border-color);
                  }}
                  
                  .permissions-list li:last-child {{
                    border-bottom: none;
                  }}
                  
                  .permission-icon {{
                    color: var(--success-color);
                    font-weight: bold;
                  }}
                  
                  .action-buttons {{
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    margin-top: 35px;
                  }}
                  
                  .btn {{
                    padding: 15px 30px;
                    border-radius: 12px;
                    font-weight: 600;
                    font-size: 1.05em;
                    text-decoration: none;
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    transition: all 0.3s ease;
                    border: none;
                    cursor: pointer;
                    position: relative;
                    overflow: hidden;
                  }}
                  
                  .btn::before {{
                    content: '';
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    width: 0;
                    height: 0;
                    background: rgba(255, 255, 255, 0.2);
                    transition: all 0.3s ease;
                    border-radius: 50%;
                    transform: translate(-50%, -50%);
                  }}
                  
                  .btn:hover::before {{
                    width: 300px;
                    height: 300px;
                  }}
                  
                  .btn-primary {{
                    background: var(--success-color);
                    color: white;
                  }}
                  
                  .btn-primary:hover {{
                    background: #2ea043;
                    transform: translateY(-2px);
                    box-shadow: 0 10px 25px rgba(35, 134, 54, 0.4);
                  }}
                  
                  .btn-secondary {{
                    background: var(--danger-color);
                    color: white;
                  }}
                  
                  .btn-secondary:hover {{
                    background: #b91c21;
                    transform: translateY(-2px);
                    box-shadow: 0 10px 25px rgba(218, 55, 61, 0.4);
                  }}
                  
                  @media (max-width: 768px) {{
                    .confirm-card {{
                      padding: 40px 30px;
                      margin: 10px;
                    }}
                    .action-buttons {{
                      flex-direction: column;
                      align-items: center;
                    }}
                    .btn {{
                      width: 100%;
                      justify-content: center;
                    }}
                  }}
                </style>
              </head>
              <body>
                <div class="confirm-card">
                  <img src="{guild_icon}" class="server-icon" loading="lazy">
                  <h2 class="confirm-title">Add Modway Bot</h2>
                  <p class="confirm-subtitle">You're about to invite Modway bot to <strong>{guild_info['name']}</strong></p>
                  
                  <div class="permissions-box">
                    <div class="permissions-title">
                      🔐 Required Permissions
                    </div>
                    <ul class="permissions-list">
                      <li><span class="permission-icon">✓</span> Administrator Access</li>
                      <li><span class="permission-icon">✓</span> Read & Send Messages</li>
                      <li><span class="permission-icon">✓</span> Manage Server Settings</li>
                      <li><span class="permission-icon">✓</span> Manage Roles & Permissions</li>
                      <li><span class="permission-icon">✓</span> Manage Channels</li>
                      <li><span class="permission-icon">✓</span> Moderation Actions</li>
                    </ul>
                  </div>
                  
                  <div class="action-buttons">
                    <a href="{invite_url}" class="btn btn-primary">
                      ✅ Confirm & Add Bot
                    </a>
                    <a href="/servers" class="btn btn-secondary">
                      ❌ Cancel
                    </a>
                  </div>
                </div>
              </body>
            </html>
            """
        
        @app.route("/manage/<guild_id>")
        def manage_server(guild_id):
            user = session.get("user")
            if not user:
                return redirect("/discord-login")
            
            access_token = session.get("access_token")
            if not access_token:
                return redirect("/discord-login")
            
            user_guilds_response = requests.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            guild_info = None
            if user_guilds_response.status_code == 200:
                guilds = user_guilds_response.json()
                guild_info = next((g for g in guilds if g["id"] == guild_id), None)
            
            guild_name = guild_info['name'] if guild_info else f"Server {guild_id}"
            guild_icon = f"https://cdn.discordapp.com/icons/{guild_info['id']}/{guild_info['icon']}.png" if guild_info and guild_info['icon'] else "https://cdn.discordapp.com/embed/avatars/0.png"
            
            cog_cards = self.generate_cog_cards(guild_id)
            
            return f"""
            <!DOCTYPE html>
            <html lang="en">
              <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Modway Dashboard - Manage {guild_name}</title>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <style>
                  :root {{
                    --primary-color: #5865f2;
                    --primary-hover: #4752c4;
                    --secondary-color: #7c3aed;
                    --background-dark: #0d1117;
                    --background-card: #161b22;
                    --text-primary: #ffffff;
                    --text-secondary: #8b949e;
                    --border-color: #30363d;
                    --success-color: #238636;
                    --danger-color: #da373d;
                    --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
                  }}
                  
                  * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                  }}
                  
                  body {{
                    font-family: 'Inter', sans-serif;
                    background: var(--background-dark);
                    color: var(--text-primary);
                    min-height: 100vh;
                    padding: 20px;
                    position: relative;
                  }}
                  
                  body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: var(--gradient-primary);
                    opacity: 0.05;
                    z-index: -1;
                  }}
                  
                  .back-btn {{
                    position: fixed;
                    top: 30px;
                    left: 30px;
                    display: inline-flex;
                    align-items: center;
                    gap: 8px;
                    background: var(--background-card);
                    border: 1px solid var(--border-color);
                    padding: 12px 20px;
                    border-radius: 12px;
                    color: var(--text-primary);
                    text-decoration: none;
                    font-weight: 500;
                    transition: all 0.3s ease;
                    backdrop-filter: blur(20px);
                    z-index: 100;
                  }}
                  
                  .back-btn:hover {{
                    background: var(--primary-color);
                    border-color: var(--primary-color);
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(88, 101, 242, 0.3);
                  }}
                  
                  .header {{
                    text-align: center;
                    margin: 60px 0 50px 0;
                    padding-top: 20px;
                  }}
                  
                  .server-info {{
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 20px;
                    margin-bottom: 30px;
                  }}
                  
                  .server-icon {{
                    width: 80px;
                    height: 80px;
                    border-radius: 20px;
                    border: 3px solid var(--primary-color);
                    box-shadow: 0 8px 20px rgba(88, 101, 242, 0.3);
                  }}
                  
                  .server-details h1 {{
                    font-size: 3em;
                    font-weight: 700;
                    background: var(--gradient-primary);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    margin-bottom: 10px;
                  }}
                  
                  .server-details p {{
                    color: var(--text-secondary);
                    font-size: 1.1em;
                  }}
                  
                  .management-section {{
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 0 20px;
                  }}
                  
                  .section-header {{
                    text-align: center;
                    margin-bottom: 50px;
                  }}
                  
                  .section-title {{
                    font-size: 2.5em;
                    font-weight: 700;
                    margin-bottom: 15px;
                    color: var(--text-primary);
                  }}
                  
                  .section-subtitle {{
                    font-size: 1.2em;
                    color: var(--text-secondary);
                    max-width: 600px;
                    margin: 0 auto;
                    line-height: 1.6;
                  }}
                  
                  .category-section {{
                    margin-bottom: 60px;
                  }}
                  
                  .category-header {{
                    display: flex;
                    align-items: center;
                    margin-bottom: 30px;
                    padding: 0 20px;
                  }}
                  
                  .category-title {{
                    font-size: 1.8em;
                    font-weight: 600;
                    color: var(--text-primary);
                    margin-right: 20px;
                  }}
                  
                  .category-divider {{
                    flex: 1;
                    height: 2px;
                    background: linear-gradient(to right, var(--primary-color), transparent);
                    border-radius: 2px;
                  }}
                  
                  .category-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
                    gap: 25px;
                    padding: 0 10px;
                  }}
                  
                  .cog-card {{
                    background: var(--background-card);
                    border: 1px solid var(--border-color);
                    border-radius: 20px;
                    padding: 0;
                    transition: all 0.4s ease;
                    position: relative;
                    overflow: hidden;
                    backdrop-filter: blur(20px);
                  }}
                  
                  .cog-card::before {{
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    height: 4px;
                    background: var(--cog-color);
                    opacity: 0;
                    transition: opacity 0.3s ease;
                  }}
                  
                  .cog-card.enabled::before {{
                    opacity: 1;
                  }}
                  
                  .cog-card:hover {{
                    transform: translateY(-8px);
                    border-color: var(--cog-color);
                    box-shadow: var(--shadow-lg);
                  }}
                  
                  .cog-card.enabled {{
                    border-color: rgba(35, 134, 54, 0.5);
                    background: linear-gradient(145deg, var(--background-card) 0%, rgba(35, 134, 54, 0.05) 100%);
                  }}
                  
                  .cog-card.disabled {{
                    border-color: rgba(218, 55, 61, 0.5);
                    background: linear-gradient(145deg, var(--background-card) 0%, rgba(218, 55, 61, 0.05) 100%);
                    opacity: 0.8;
                  }}
                  
                  .cog-card-inner {{
                    padding: 25px;
                  }}
                  
                  .cog-header {{
                    display: flex;
                    align-items: flex-start;
                    justify-content: space-between;
                    margin-bottom: 20px;
                  }}
                  
                  .cog-title {{
                    display: flex;
                    align-items: center;
                    gap: 15px;
                    flex: 1;
                  }}
                  
                  .cog-icon {{
                    font-size: 2.5em;
                    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));
                  }}
                  
                  .cog-info {{
                    display: flex;
                    flex-direction: column;
                  }}
                  
                  .cog-name {{
                    font-size: 1.4em;
                    font-weight: 600;
                    margin: 0 0 5px 0;
                    color: var(--text-primary);
                  }}
                  
                  .cog-category {{
                    font-size: 0.85em;
                    color: var(--text-secondary);
                    background: rgba(255, 255, 255, 0.1);
                    padding: 2px 8px;
                    border-radius: 12px;
                    width: fit-content;
                  }}
                  
                  .toggle-container {{
                    flex-shrink: 0;
                  }}
                  
                  .toggle-switch {{
                    position: relative;
                    width: 60px;
                    height: 32px;
                    background: var(--danger-color);
                    border-radius: 16px;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    border: 2px solid var(--danger-color);
                  }}
                  
                  .toggle-switch.enabled {{
                    background: var(--success-color);
                    border-color: var(--success-color);
                  }}
                  
                  .toggle-switch:hover {{
                    transform: scale(1.05);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
                  }}
                  
                  .toggle-slider {{
                    position: absolute;
                    top: 2px;
                    left: 2px;
                    width: 24px;
                    height: 24px;
                    background: white;
                    border-radius: 50%;
                    transition: all 0.3s ease;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                  }}
                  
                  .toggle-switch.enabled .toggle-slider {{
                    transform: translateX(28px);
                  }}
                  
                  .cog-description {{
                    color: var(--text-secondary);
                    line-height: 1.6;
                    margin-bottom: 20px;
                    font-size: 0.95em;
                  }}
                  
                  .cog-status {{
                    display: flex;
                    justify-content: center;
                  }}
                  
                  .status-indicator {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: 500;
                    font-size: 0.9em;
                    transition: all 0.3s ease;
                  }}
                  
                  .cog-card.enabled .status-indicator {{
                    background: rgba(35, 134, 54, 0.2);
                    color: #3fb950;
                    border: 1px solid rgba(35, 134, 54, 0.3);
                  }}
                  
                  .cog-card.disabled .status-indicator {{
                    background: rgba(218, 55, 61, 0.2);
                    color: #ff7b82;
                    border: 1px solid rgba(218, 55, 61, 0.3);
                  }}
                  
                  .config-btn {{
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 6px 12px;
                    background: var(--primary-color);
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    font-size: 0.8em;
                    font-weight: 500;
                    margin-left: 10px;
                    transition: all 0.3s ease;
                  }}
                  
                  .config-btn:hover {{
                    background: var(--primary-hover);
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(88, 101, 242, 0.3);
                  }}
                  
                  .status-dot {{
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                  }}
                  
                  .status-dot.enabled {{
                    background: #3fb950;
                  }}
                  
                  .status-dot.disabled {{
                    background: #ff7b82;
                  }}
                  
                  @keyframes pulse {{
                    0% {{ opacity: 1; }}
                    50% {{ opacity: 0.5; }}
                    100% {{ opacity: 1; }}
                  }}
                  
                  .loading-overlay {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.7);
                    display: none;
                    align-items: center;
                    justify-content: center;
                    z-index: 1000;
                  }}
                  
                  .loading-spinner {{
                    width: 50px;
                    height: 50px;
                    border: 4px solid var(--border-color);
                    border-top: 4px solid var(--primary-color);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                  }}
                  
                  @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                  }}
                  
                  @media (max-width: 768px) {{
                    .back-btn {{
                      position: static;
                      margin: 20px auto;
                      display: flex;
                      width: fit-content;
                    }}
                    .header {{ margin-top: 20px; }}
                    .server-info {{ flex-direction: column; gap: 15px; }}
                    .server-icon {{ width: 60px; height: 60px; }}
                    .server-details h1 {{ font-size: 2.2em; }}
                    .category-grid {{ grid-template-columns: 1fr; }}
                    .cog-card {{ margin: 0 5px; }}
                    .section-title {{ font-size: 2em; }}
                  }}
                </style>
                <script>
                  let isToggling = false;
                  
                  async function toggleCog(guildId, cogName) {{
                    if (isToggling) return;
                    isToggling = true;
                    
                    const loadingOverlay = document.querySelector('.loading-overlay');
                    loadingOverlay.style.display = 'flex';
                    
                    try {{
                      const response = await fetch(`/api/toggle-cog/${{guildId}}/${{cogName}}`, {{
                        method: 'POST',
                        headers: {{
                          'Content-Type': 'application/json',
                        }}
                      }});
                      
                      if (response.ok) {{
                        // Add a small delay for better UX
                        setTimeout(() => {{
                          location.reload();
                        }}, 800);
                      }} else {{
                        const error = await response.json();
                        alert(`Failed to toggle cog: ${{error.error || 'Unknown error'}}`);
                        loadingOverlay.style.display = 'none';
                        isToggling = false;
                      }}
                    }} catch (error) {{
                      console.error('Error:', error);
                      alert('An error occurred. Please try again.');
                      loadingOverlay.style.display = 'none';
                      isToggling = false;
                    }}
                  }}
                  
                  // Add smooth scroll behavior
                  document.documentElement.style.scrollBehavior = 'smooth';
                </script>
              </head>
              <body>
                <a href="/servers" class="back-btn">← Back to Servers</a>
                
                <div class="header">
                  <div class="server-info">
                    <img src="{guild_icon}" class="server-icon" loading="lazy">
                    <div class="server-details">
                      <h1>{guild_name}</h1>
                      <p>Bot Feature Management</p>
                    </div>
                  </div>
                </div>
                
                <div class="management-section">
                  <div class="section-header">
                    <h2 class="section-title">🔧 Configure Bot Features</h2>
                    <p class="section-subtitle">Enable or disable specific bot functionalities for your server. Changes take effect immediately.</p>
                  </div>
                  
                  {cog_cards}
                </div>
                
                <div class="loading-overlay">
                  <div class="loading-spinner"></div>
                </div>
              </body>
            </html>
            """

        # AutoRole Configuration Route
        @app.route("/config/autorole/<guild_id>")
        def autorole_config(guild_id):
            user = session.get("user")
            if not user:
                return redirect("/discord-login")
            
            access_token = session.get("access_token")
            if not access_token:
                return redirect("/discord-login")
            
            # Verify permissions
            user_guilds_response = requests.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_guilds_response.status_code != 200:
                return "❌ Failed to fetch your servers."
            
            user_guilds = user_guilds_response.json()
            guild_info = next((g for g in user_guilds if g["id"] == guild_id), None)
            
            if not guild_info or not (int(guild_info["permissions"]) & 0x20):
                return "❌ No permission to manage this server."
            
            # Load AutoRole settings
            autorole_data = load_autorole_settings()
            current_role_id = autorole_data.get(guild_id, None)
            
            # Get guild roles from bot
            try:
                roles_response = requests.get(
                    f"https://discord.com/api/guilds/{guild_id}/roles",
                    headers={"Authorization": f"Bot {Token}"}
                )
                roles = roles_response.json() if roles_response.status_code == 200 else []
                # Sort roles by position (highest first)
                roles = sorted(roles, key=lambda r: r.get("position", 0), reverse=True)
            except:
                roles = []
            
            guild_name = guild_info['name']
            guild_icon = f"https://cdn.discordapp.com/icons/{guild_info['id']}/{guild_info['icon']}.png" if guild_info['icon'] else "https://cdn.discordapp.com/embed/avatars/0.png"
            
            # Generate role options for dropdown
            role_options = '<option value="">No Auto Role</option>'
            for role in roles:
                if role['name'] != '@everyone':  # Skip @everyone role
                    selected = "selected" if str(role['id']) == str(current_role_id) else ""
                    color_hex = f"#{role['color']:06x}" if role['color'] else "#99AAB5"
                    role_options += f'<option value="{role["id"]}" {selected} style="color: {color_hex};">{role["name"]}</option>'
            
            return f"""
            <!DOCTYPE html>
            <html lang="en">
              <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AutoRole Configuration - {guild_name}</title>
                <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <style>
                  :root {{
                    --primary-color: #5865f2;
                    --primary-hover: #4752c4;
                    --secondary-color: #7c3aed;
                    --background-dark: #0d1117;
                    --background-card: #161b22;
                    --text-primary: #ffffff;
                    --text-secondary: #8b949e;
                    --border-color: #30363d;
                    --success-color: #238636;
                    --warning-color: #f85149;
                    --gradient-primary: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
                  }}
                  
                  * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                  }}
                  
                  body {{
                    font-family: 'Inter', sans-serif;
                    background: var(--background-dark);
                    color: var(--text-primary);
                    min-height: 100vh;
                    padding: 20px;
                    position: relative;
                  }}
                  
                  body::before {{
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: var(--gradient-primary);
                    opacity: 0.05;
                    z-index: -1;
                  }}
                  
                  .header {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 30px;
                    padding: 20px;
                    background: var(--background-card);
                    border-radius: 15px;
                    border: 1px solid var(--border-color);
                  }}
                  
                  .header-info {{
                    display: flex;
                    align-items: center;
                    gap: 15px;
                  }}
                  
                  .guild-icon {{
                    width: 50px;
                    height: 50px;
                    border-radius: 12px;
                    border: 2px solid var(--primary-color);
                  }}
                  
                  .header-text h1 {{
                    font-size: 1.8em;
                    margin-bottom: 5px;
                    background: var(--gradient-primary);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                  }}
                  
                  .header-text p {{
                    color: var(--text-secondary);
                    font-size: 0.9em;
                  }}
                  
                  .back-btn {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    background: var(--background-dark);
                    border: 1px solid var(--border-color);
                    padding: 10px 20px;
                    border-radius: 10px;
                    color: var(--text-primary);
                    text-decoration: none;
                    transition: all 0.3s ease;
                  }}
                  
                  .back-btn:hover {{
                    background: var(--primary-color);
                    border-color: var(--primary-color);
                    transform: translateY(-2px);
                  }}
                  
                  .config-container {{
                    max-width: 800px;
                    margin: 0 auto;
                    display: grid;
                    grid-template-columns: 1fr;
                    gap: 25px;
                  }}
                  
                  .config-section {{
                    background: var(--background-card);
                    border: 1px solid var(--border-color);
                    border-radius: 15px;
                    padding: 25px;
                    transition: all 0.3s ease;
                  }}
                  
                  .config-section:hover {{
                    border-color: var(--primary-color);
                    box-shadow: 0 5px 15px rgba(88, 101, 242, 0.1);
                  }}
                  
                  .section-header {{
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 1px solid var(--border-color);
                  }}
                  
                  .section-icon {{
                    font-size: 1.5em;
                  }}
                  
                  .section-title {{
                    font-size: 1.4em;
                    font-weight: 600;
                  }}
                  
                  .form-group {{
                    margin-bottom: 20px;
                  }}
                  
                  .form-label {{
                    display: block;
                    margin-bottom: 8px;
                    font-weight: 500;
                    color: var(--text-primary);
                  }}
                  
                  .form-select {{
                    width: 100%;
                    padding: 12px 15px;
                    background: var(--background-dark);
                    border: 1px solid var(--border-color);
                    border-radius: 8px;
                    color: var(--text-primary);
                    font-family: inherit;
                    transition: all 0.3s ease;
                  }}
                  
                  .form-select:focus {{
                    outline: none;
                    border-color: var(--primary-color);
                    box-shadow: 0 0 0 3px rgba(88, 101, 242, 0.1);
                  }}
                  
                  .form-help {{
                    font-size: 0.85em;
                    color: var(--text-secondary);
                    margin-top: 5px;
                    line-height: 1.4;
                  }}
                  
                  .info-box {{
                    background: rgba(88, 101, 242, 0.1);
                    border: 1px solid rgba(88, 101, 242, 0.3);
                    border-radius: 8px;
                    padding: 15px;
                    margin: 20px 0;
                  }}
                  
                  .info-box-title {{
                    font-weight: 600;
                    margin-bottom: 8px;
                    color: var(--primary-color);
                    display: flex;
                    align-items: center;
                    gap: 8px;
                  }}
                  
                  .info-box-content {{
                    color: var(--text-secondary);
                    font-size: 0.9em;
                    line-height: 1.5;
                  }}
                  
                  .action-buttons {{
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    margin-top: 30px;
                  }}
                  
                  .btn {{
                    padding: 12px 30px;
                    border-radius: 10px;
                    font-weight: 600;
                    text-decoration: none;
                    border: none;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    font-family: inherit;
                    font-size: 1em;
                  }}
                  
                  .btn-primary {{
                    background: var(--success-color);
                    color: white;
                  }}
                  
                  .btn-primary:hover {{
                    background: #2ea043;
                    transform: translateY(-2px);
                    box-shadow: 0 8px 20px rgba(35, 134, 54, 0.3);
                  }}
                  
                  .btn-secondary {{
                    background: var(--background-dark);
                    color: var(--text-primary);
                    border: 1px solid var(--border-color);
                  }}
                  
                  .btn-secondary:hover {{
                    background: var(--border-color);
                    transform: translateY(-2px);
                  }}
                  
                  .status-message {{
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    display: none;
                  }}
                  
                  .status-message.success {{
                    background: rgba(35, 134, 54, 0.2);
                    border: 1px solid rgba(35, 134, 54, 0.3);
                    color: #3fb950;
                  }}
                  
                  .status-message.error {{
                    background: rgba(218, 55, 61, 0.2);
                    border: 1px solid rgba(218, 55, 61, 0.3);
                    color: #ff7b82;
                  }}
                  
                  @media (max-width: 768px) {{
                    .header {{
                      flex-direction: column;
                      gap: 15px;
                      text-align: center;
                    }}
                    
                    .action-buttons {{
                      flex-direction: column;
                    }}
                  }}
                </style>
              </head>
              <body>
                <div class="header">
                  <div class="header-info">
                    <img src="{guild_icon}" class="guild-icon" loading="lazy">
                    <div class="header-text">
                      <h1>🎭 AutoRole Configuration</h1>
                      <p>Configure automatic role assignment for {guild_name}</p>
                    </div>
                  </div>
                  <a href="/manage/{guild_id}" class="back-btn">← Back to Dashboard</a>
                </div>
                
                <div class="config-container">
                  <div id="status-message" class="status-message"></div>
                  
                  <div class="config-section">
                    <div class="section-header">
                      <div class="section-icon">👑</div>
                      <div class="section-title">Role Assignment</div>
                    </div>
                    
                    <div class="form-group">
                      <label class="form-label" for="autorole_select">Role to assign to new members:</label>
                      <select class="form-select" id="autorole_select">
                        {role_options}
                      </select>
                      <div class="form-help">This role will be automatically assigned when new members join your server.</div>
                    </div>
                    
                    <div class="info-box">
                      <div class="info-box-title">
                        <span>ℹ️</span>
                        <span>How AutoRole works</span>
                      </div>
                      <div class="info-box-content">
                        <p>When new members join your server, they will automatically receive the selected role. This happens instantly when they join.</p>
                        <br>
                        <p>If you select "No Auto Role" option, no role will be assigned automatically.</p>
                      </div>
                    </div>
                    
                    <div class="action-buttons">
                      <button id="save_button" class="btn btn-primary">💾 Save Settings</button>
                      <button id="reset_button" class="btn btn-secondary">🔄 Reset</button>
                    </div>
                  </div>
                </div>
                
                <script>
                  document.getElementById('save_button').addEventListener('click', async function() {
                    const roleId = document.getElementById('autorole_select').value;
                    const statusMessage = document.getElementById('status-message');
                    
                    statusMessage.textContent = 'Saving settings...';
                    statusMessage.className = 'status-message';
                    statusMessage.style.display = 'block';
                    statusMessage.style.background = 'rgba(255, 255, 255, 0.1)';
                    statusMessage.style.color = 'var(--text-primary)';
                    statusMessage.style.border = '1px solid var(--border-color)';
                    
                    try {
                      const response = await fetch('/api/autorole/save/{guild_id}', {
                        method: 'POST',
                        headers: {
                          'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ roleId: roleId })
                      });
                      
                      const result = await response.json();
                      
                      if (result.success) {
                        statusMessage.textContent = '✅ AutoRole settings saved successfully!';
                        statusMessage.className = 'status-message success';
                      } else {
                        statusMessage.textContent = '❌ ' + (result.error || 'An error occurred');
                        statusMessage.className = 'status-message error';
                      }
                    } catch (error) {
                      console.error('Error:', error);
                      statusMessage.textContent = '❌ An error occurred while saving settings';
                      statusMessage.className = 'status-message error';
                    }
                  });
                  
                  document.getElementById('reset_button').addEventListener('click', function() {
                    if (confirm('Reset to the current saved settings?')) {
                      location.reload();
                    }
                  });
                </script>
              </body>
            </html>
            """
        
        @app.route("/api/autorole/save/<guild_id>", methods=["POST"])
        def save_autorole_config(guild_id):
            user = session.get("user")
            if not user:
                return jsonify({"success": False, "error": "Not authenticated"}), 401
            
            access_token = session.get("access_token")
            if not access_token:
                return jsonify({"success": False, "error": "No access token"}), 401
            
            # Verify permissions
            user_guilds_response = requests.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_guilds_response.status_code != 200:
                return jsonify({"success": False, "error": "Failed to fetch guilds"}), 403
            
            user_guilds = user_guilds_response.json()
            guild = next((g for g in user_guilds if g["id"] == guild_id), None)
            
            if not guild or not (int(guild["permissions"]) & 0x20):
                return jsonify({"success": False, "error": "No permission to manage this server"}), 403
            
            # Check if AutoRole module is enabled
            if not self.get_cog_status(guild_id, "AutoRole"):
                return jsonify({"success": False, "error": "AutoRole module is disabled"}), 400
            
            # Save AutoRole settings
            try:
                data = request.get_json()
                role_id = data.get("roleId")
                
                autorole_settings = load_autorole_settings()
                
                if role_id:
                    # Verify the role exists in the server
                    roles_response = requests.get(
                        f"https://discord.com/api/guilds/{guild_id}/roles",
                        headers={"Authorization": f"Bot {Token}"}
                    )
                    
                    if roles_response.status_code == 200:
                        roles = roles_response.json()
                        role_exists = any(r["id"] == role_id for r in roles)
                        
                        if not role_exists:
                            return jsonify({"success": False, "error": "Selected role does not exist in this server"}), 400
                    
                    autorole_settings[guild_id] = role_id
                else:
                    # Remove setting if role_id is empty
                    if guild_id in autorole_settings:
                        del autorole_settings[guild_id]
                
                save_autorole_settings(autorole_settings)
                
                # Reload settings in autorole cog if it's loaded
                for cog_name, cog in self.bot.cogs.items():
                    if cog_name == "AutoRole" and hasattr(cog, "reload_settings"):
                        cog.reload_settings()
                        break
                
                return jsonify({"success": True, "message": "AutoRole settings saved successfully"})
            except Exception as e:
                return jsonify({"success": False, "error": f"Failed to save settings: {str(e)}"}), 500

        @app.route("/api/toggle-cog/<guild_id>/<cog_name>", methods=["POST"])
        def toggle_cog(guild_id, cog_name):
            user = session.get("user")
            if not user:
                return jsonify({"error": "Not authenticated"}), 401
            
            # Check if user has permission to manage this guild
            access_token = session.get("access_token")
            if not access_token:
                return jsonify({"error": "No access token"}), 401
            
            user_guilds_response = requests.get(
                "https://discord.com/api/users/@me/guilds",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if user_guilds_response.status_code != 200:
                return jsonify({"error": "Failed to fetch guilds"}), 403
            
            user_guilds = user_guilds_response.json()
            guild = next((g for g in user_guilds if g["id"] == guild_id), None)
            
            if not guild or not (int(guild["permissions"]) & 0x20):  # Manage Server permission
                return jsonify({"error": "No permission to manage this server"}), 403
            
            if cog_name not in AVAILABLE_COGS:
                return jsonify({"error": "Invalid cog name"}), 400
            
            # Toggle the cog status
            current_status = self.get_cog_status(guild_id, cog_name)
            new_status = not current_status
            self.set_cog_status(guild_id, cog_name, new_status)
            
            return jsonify({
                "success": True,
                "cog_name": cog_name,
                "enabled": new_status,
                "message": f"Successfully {'enabled' if new_status else 'disabled'} {AVAILABLE_COGS[cog_name]['name']}"
            })

        port = int(os.environ.get("PORT", 5379))
        thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=port))
        thread.start()

async def setup(bot):
    await bot.add_cog(ModwayDashboard(bot))
