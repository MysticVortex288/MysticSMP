import discord
from typing import Optional, Dict, Any, Union

class EmbedCreator:
    """Class to create Discord embeds for various purposes."""
    
    @staticmethod
    def create_welcome_embed(
        user: discord.Member, 
        inviter: Optional[discord.Member] = None,
        message: str = None,
        color: Union[int, str] = None
    ) -> discord.Embed:
        """
        Create a welcome embed for a new server member.
        
        Args:
            user: The Discord user that joined
            inviter: The member who invited them (if known)
            message: Custom welcome message
            color: Embed color (hex string or int)
            
        Returns:
            discord.Embed: The formatted welcome embed
        """
        # Default welcome message if none provided
        if not message:
            message = "Welcome to the server!"
            
        # Format the message with user and inviter information
        formatted_message = message.format(
            user=user.name,
            user_mention=user.mention,
            user_tag=str(user),
            user_id=user.id,
            server=user.guild.name,
            inviter=inviter.mention if inviter else "Unknown",
            inviter_name=inviter.name if inviter else "Unknown",
            inviter_tag=str(inviter) if inviter else "Unknown",
            member_count=user.guild.member_count
        )
        
        # Parse color
        embed_color = 0x3498db  # Default blue color
        if color:
            if isinstance(color, str) and color.startswith("0x"):
                try:
                    embed_color = int(color, 16)
                except ValueError:
                    pass
            elif isinstance(color, int):
                embed_color = color
        
        # Create the embed
        embed = discord.Embed(
            title=f"Welcome to {user.guild.name}!",
            description=formatted_message,
            color=embed_color
        )
        
        # Add user avatar
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Add timestamps and footer
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=f"Member #{user.guild.member_count}")
        
        return embed
    
    @staticmethod
    def create_help_embed(
        title: str,
        description: str,
        commands: Dict[str, str],
        color: int = 0x3498db
    ) -> discord.Embed:
        """
        Create a help embed displaying command information.
        
        Args:
            title: The title of the help embed
            description: A general description for the help embed
            commands: Dictionary mapping command names to descriptions
            color: Embed color
            
        Returns:
            discord.Embed: The formatted help embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        # Add each command to the embed
        for name, desc in commands.items():
            embed.add_field(name=name, value=desc, inline=False)
        
        # Add timestamps and footer
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text="Use !help <command> for more information.")
        
        return embed
    
    @staticmethod
    def create_error_embed(title: str, description: str) -> discord.Embed:
        """
        Create an error embed.
        
        Args:
            title: The title of the error embed
            description: A description explaining the error
            
        Returns:
            discord.Embed: The formatted error embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=0xe74c3c  # Red color for errors
        )
        
        # Add timestamps
        embed.timestamp = discord.utils.utcnow()
        
        return embed
    
    @staticmethod
    def create_success_embed(title: str, description: str) -> discord.Embed:
        """
        Create a success embed.
        
        Args:
            title: The title of the success embed
            description: A description explaining the success
            
        Returns:
            discord.Embed: The formatted success embed
        """
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x2ecc71  # Green color for success
        )
        
        # Add timestamps
        embed.timestamp = discord.utils.utcnow()
        
        return embed
