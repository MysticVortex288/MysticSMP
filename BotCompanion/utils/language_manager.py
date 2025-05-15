import json
import os
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger('discord_bot')

class LanguageManager:
    """Manages translations and language preferences for users."""
    
    def __init__(self):
        """Initialize the language manager."""
        self.translations_file = "translations.json"
        self.user_languages_file = "user_languages.json"
        self.guild_languages_file = "guild_languages.json"
        self.translations = self._load_translations()
        self.user_languages = self._load_user_languages()
        self.guild_languages = self._load_guild_languages()
        self.available_languages = list(self.translations.keys())
        self.default_language = "de"  # Default to German
    
    def _load_translations(self) -> Dict[str, Dict[str, Any]]:
        """Load translations from file."""
        try:
            with open(self.translations_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading translations: {e}")
            # Return a minimal translation set to prevent crashes
            return {
                "de": {"general": {"error": "Fehler"}},
                "en": {"general": {"error": "Error"}}
            }
    
    def _load_user_languages(self) -> Dict[str, str]:
        """Load user language preferences from file."""
        try:
            with open(self.user_languages_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create a new file with an empty dictionary
            self._save_user_languages({})
            return {}
    
    def _load_guild_languages(self) -> Dict[str, str]:
        """Load guild language preferences from file."""
        try:
            with open(self.guild_languages_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Create a new file with an empty dictionary
            self._save_guild_languages({})
            return {}
    
    def _save_user_languages(self, data=None):
        """Save user language preferences to file."""
        if data is None:
            data = self.user_languages
        
        with open(self.user_languages_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def _save_guild_languages(self, data=None):
        """Save guild language preferences to file."""
        if data is None:
            data = self.guild_languages
        
        with open(self.guild_languages_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    
    def set_user_language(self, user_id: int, language: str) -> bool:
        """
        Set a user's preferred language.
        
        Args:
            user_id: The Discord user ID
            language: The language code to set (e.g., 'en', 'de')
            
        Returns:
            bool: True if the language was set successfully, False otherwise
        """
        if language not in self.available_languages:
            return False
        
        self.user_languages[str(user_id)] = language
        self._save_user_languages()
        return True
    
    def set_guild_language(self, guild_id: int, language: str) -> bool:
        """
        Set a guild's preferred language.
        
        Args:
            guild_id: The Discord guild ID
            language: The language code to set (e.g., 'en', 'de')
            
        Returns:
            bool: True if the language was set successfully, False otherwise
        """
        if language not in self.available_languages:
            return False
        
        self.guild_languages[str(guild_id)] = language
        self._save_guild_languages()
        return True
    
    def get_user_language(self, user_id: int) -> str:
        """
        Get a user's preferred language.
        
        Args:
            user_id: The Discord user ID
            
        Returns:
            str: The user's preferred language code, or the default language if not set
        """
        return self.user_languages.get(str(user_id), self.default_language)
    
    def get_guild_language(self, guild_id: int) -> str:
        """
        Get a guild's preferred language.
        
        Args:
            guild_id: The Discord guild ID
            
        Returns:
            str: The guild's preferred language code, or the default language if not set
        """
        return self.guild_languages.get(str(guild_id), self.default_language)
    
    def get_text(self, key_path: str, language: str = "", **format_args) -> str:
        """
        Get a translated text by key path.
        
        Args:
            key_path: The path to the text in the translations (e.g., 'general.success')
            language: The language to use, or None to use the default language
            **format_args: Arguments to format the text with
            
        Returns:
            str: The translated text, or the key path if the text was not found
        """
        if not language:
            language = self.default_language
        
        if language not in self.available_languages:
            language = self.default_language
        
        # Split the key path
        parts = key_path.split('.')
        
        # Navigate the translations dictionary
        current = self.translations[language]
        for part in parts:
            if part not in current:
                # If the key is not found, return the key path
                return key_path
            current = current[part]
        
        # Format the text if it's a string
        if isinstance(current, str):
            try:
                return current.format(**format_args)
            except KeyError as e:
                logger.error(f"Key error when formatting text '{key_path}': {e}")
                return current
        
        # If the result is not a string, return the key path
        return key_path
    
    def get_user_text(self, user_id: int, key_path: str, **format_args) -> str:
        """
        Get a translated text for a user.
        
        Args:
            user_id: The Discord user ID
            key_path: The path to the text in the translations
            **format_args: Arguments to format the text with
            
        Returns:
            str: The translated text, or the key path if the text was not found
        """
        language = self.get_user_language(user_id)
        return self.get_text(key_path, language, **format_args)
    
    def get_guild_text(self, guild_id: int, key_path: str, **format_args) -> str:
        """
        Get a translated text for a guild.
        
        Args:
            guild_id: The Discord guild ID
            key_path: The path to the text in the translations
            **format_args: Arguments to format the text with
            
        Returns:
            str: The translated text, or the key path if the text was not found
        """
        language = self.get_guild_language(guild_id)
        return self.get_text(key_path, language, **format_args)
    
    def get_context_text(self, ctx, key_path: str, **format_args) -> str:
        """
        Get a translated text for a command context.
        Prioritizes user language over guild language.
        
        Args:
            ctx: The Discord command context
            key_path: The path to the text in the translations
            **format_args: Arguments to format the text with
            
        Returns:
            str: The translated text, or the key path if the text was not found
        """
        user_id = ctx.author.id
        guild_id = ctx.guild.id if ctx.guild else None
        
        # First try user language
        language = self.get_user_language(user_id)
        
        # If no user language is set and we're in a guild, try guild language
        if language == self.default_language and guild_id is not None:
            language = self.get_guild_language(guild_id)
        
        return self.get_text(key_path, language, **format_args)
    
    def get_available_languages(self) -> List[str]:
        """
        Get a list of available languages.
        
        Returns:
            List[str]: List of available language codes
        """
        return self.available_languages