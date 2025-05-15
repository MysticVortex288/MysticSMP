import json
import os
import logging
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger('discord_bot')

class ConfigManager:
    """Class to manage the configuration and persistent data for the bot."""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load the configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file {self.config_file} not found. Creating a new one.")
                self._save_config({
                    "prefix": "!",
                    "default_welcome_message": "Welcome to the server, {user_mention}! You were invited by {inviter}.",
                    "default_welcome_channel": None,
                    "default_welcome_enabled": False,
                    "default_welcome_embed_color": "0x3498db",
                    "default_welcome_embed_enabled": True,
                    "guilds": {}
                })
                return self._load_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {
                "prefix": "!",
                "guilds": {}
            }
            
    def _save_config(self, config: Dict[str, Any] = None) -> None:
        """Save the configuration to file."""
        if config is None:
            config = self.config
            
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            self.config = config
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            
    def get_prefix(self) -> str:
        """Get the command prefix."""
        return self.config.get("prefix", "!")
        
    def set_prefix(self, prefix: str) -> None:
        """Set the command prefix."""
        self.config["prefix"] = prefix
        self._save_config()
        
    def get_guild_config(self, guild_id: int) -> Dict[str, Any]:
        """Get the configuration for a specific guild."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.config["guilds"]:
            self.config["guilds"][guild_id_str] = self._create_default_guild_config()
            self._save_config()
        return self.config["guilds"][guild_id_str]
        
    def _create_default_guild_config(self) -> Dict[str, Any]:
        """Create a default configuration for a guild."""
        return {
            "welcome_channel": self.config.get("default_welcome_channel"),
            "welcome_message": self.config.get("default_welcome_message"),
            "welcome_enabled": self.config.get("default_welcome_enabled", False),
            "welcome_embed_color": self.config.get("default_welcome_embed_color", "0x3498db"),
            "welcome_embed_enabled": self.config.get("default_welcome_embed_enabled", True),
            "invites": {}
        }
        
    def update_guild_config(self, guild_id: int, key: str, value: Any) -> None:
        """Update a specific configuration value for a guild."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.config["guilds"]:
            self.get_guild_config(guild_id)
        
        self.config["guilds"][guild_id_str][key] = value
        self._save_config()
        
    def get_invite_data(self, guild_id: int) -> Dict[str, Any]:
        """Get the invite data for a specific guild."""
        guild_config = self.get_guild_config(guild_id)
        return guild_config.get("invites", {})
        
    def update_invite_data(self, guild_id: int, invite_code: str, data: Dict[str, Any]) -> None:
        """Update the invite data for a specific guild and invite code."""
        guild_id_str = str(guild_id)
        if guild_id_str not in self.config["guilds"]:
            self.get_guild_config(guild_id)
            
        if "invites" not in self.config["guilds"][guild_id_str]:
            self.config["guilds"][guild_id_str]["invites"] = {}
            
        self.config["guilds"][guild_id_str]["invites"][invite_code] = data
        self._save_config()
        
    def remove_invite_data(self, guild_id: int, invite_code: str) -> None:
        """Remove the invite data for a specific guild and invite code."""
        guild_id_str = str(guild_id)
        if guild_id_str in self.config["guilds"]:
            if "invites" in self.config["guilds"][guild_id_str]:
                if invite_code in self.config["guilds"][guild_id_str]["invites"]:
                    del self.config["guilds"][guild_id_str]["invites"][invite_code]
                    self._save_config()
