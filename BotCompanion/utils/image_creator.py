import os
import io
import logging
import aiohttp
import discord
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from typing import Tuple, Optional

logger = logging.getLogger('discord_bot')

class ImageCreator:
    """Class to create customized images for various purposes."""
    
    # Cache for downloaded fonts
    _font_cache = {}
    
    @staticmethod
    async def _download_avatar(avatar_url: str) -> Optional[bytes]:
        """
        Downloads a user's avatar from Discord.
        
        Args:
            avatar_url: The URL of the user's avatar
            
        Returns:
            The avatar as bytes, or None if it couldn't be downloaded
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(avatar_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download avatar: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error downloading avatar: {e}")
            return None
    
    @classmethod
    def _get_font(cls, size: int = 36, bold: bool = False) -> ImageFont.FreeTypeFont:
        """
        Gets a font with the specified size. Caches fonts for reuse.
        
        Args:
            size: Font size in points
            bold: Whether to use bold font
            
        Returns:
            A PIL ImageFont object
        """
        font_key = f"{'bold' if bold else 'regular'}_{size}"
        
        if font_key in cls._font_cache:
            return cls._font_cache[font_key]
        
        # Default system fonts that are likely to be available
        font_paths = [
            # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            # Windows
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            # macOS
            "/Library/Fonts/Arial.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            # Web safe font fallback
            "./fonts/roboto.ttf",
            "./fonts/roboto-bold.ttf"
        ]
        
        # Determine if we need the regular or bold font
        font_index = 1 if bold else 0
        
        # Try to load the first available font
        for i in range(0, len(font_paths), 2):
            try:
                font_path = font_paths[i + font_index]
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, size)
                    cls._font_cache[font_key] = font
                    return font
            except Exception as e:
                logger.debug(f"Could not load font {font_path}: {e}")
                
        # Fallback to default
        logger.warning("Using default font as no system fonts were found")
        font = ImageFont.load_default()
        cls._font_cache[font_key] = font
        return font
    
    @classmethod
    async def create_welcome_image(
        cls,
        user: discord.Member,
        server_name: str,
        width: int = 1000,
        height: int = 300,
        background_color: Tuple[int, int, int] = (44, 47, 51),  # Discord dark theme color
        accent_color: Tuple[int, int, int] = (114, 137, 218)    # Discord blurple
    ) -> Optional[discord.File]:
        """
        Creates a welcome image for a new server member.
        
        Args:
            user: The Discord user that joined
            server_name: The name of the Discord server
            width: Width of the image in pixels
            height: Height of the image in pixels
            background_color: RGB tuple for the background color
            accent_color: RGB tuple for the accent color
            
        Returns:
            discord.File: The image as a Discord file object, or None if it couldn't be created
        """
        try:
            # Create base image
            image = Image.new('RGB', (width, height), background_color)
            draw = ImageDraw.Draw(image)
            
            # Add a decorative element (curved line across)
            for i in range(5):
                y_pos = height // 4 + i * 3
                draw.line([(0, y_pos), (width, y_pos)], fill=accent_color, width=1)
            
            # Add rounded rectangle for content area
            rect_pad = 20
            rect_height = height - 2 * rect_pad
            rect_width = width - 2 * rect_pad
            
            # Create a mask for rounded corners
            mask = Image.new('L', (rect_width, rect_height), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.rounded_rectangle([(0, 0), (rect_width, rect_height)], radius=15, fill=255)
            
            # Draw slightly darker background rectangle
            darker_bg = tuple(max(0, c - 10) for c in background_color)
            rect_img = Image.new('RGB', (rect_width, rect_height), darker_bg)
            image.paste(rect_img, (rect_pad, rect_pad), mask)
            
            # Download avatar
            avatar_bytes = await cls._download_avatar(str(user.display_avatar.url))
            if not avatar_bytes:
                # Create a placeholder avatar if download fails
                avatar = Image.new('RGB', (128, 128), accent_color)
                avatar_draw = ImageDraw.Draw(avatar)
                avatar_draw.text((64, 64), user.name[0].upper(), fill=(255, 255, 255), 
                                font=cls._get_font(60, True), anchor="mm")
            else:
                # Open the avatar image from bytes
                avatar = Image.open(io.BytesIO(avatar_bytes))
                avatar = avatar.convert('RGB')
                avatar = avatar.resize((128, 128))
            
            # Make avatar circular
            mask = Image.new('L', avatar.size, 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, 128, 128), fill=255)
            
            # Apply blur to the avatar for a glow effect
            avatar_glow = avatar.copy()
            avatar_glow = avatar_glow.filter(ImageFilter.GaussianBlur(5))
            
            # Paste the glow behind the avatar
            image.paste(avatar_glow, (rect_pad + 40 - 5, rect_pad + rect_height//2 - 64 - 5), 
                        mask.resize((138, 138)))
            
            # Paste the avatar
            image.paste(avatar, (rect_pad + 40, rect_pad + rect_height//2 - 64), mask)
            
            # Add text
            title_font = cls._get_font(40, True)
            subtitle_font = cls._get_font(30)
            
            # Welcome text
            welcome_text = "WILLKOMMEN"
            text_width = title_font.getbbox(welcome_text)[2] - title_font.getbbox(welcome_text)[0]
            draw.text(
                (rect_pad + 200, rect_pad + 40),
                welcome_text,
                fill=accent_color,
                font=title_font
            )
            
            # Draw a short line under the welcome text
            line_y = rect_pad + 80
            draw.line(
                [(rect_pad + 200, line_y), (rect_pad + 200 + text_width, line_y)],
                fill=accent_color,
                width=2
            )
            
            # Username
            # Truncate long usernames
            display_name = user.display_name
            if len(display_name) > 20:
                display_name = display_name[:17] + "..."
                
            draw.text(
                (rect_pad + 200, rect_pad + 100),
                display_name,
                fill=(255, 255, 255),
                font=title_font
            )
            
            # Server name
            if len(server_name) > 30:
                server_name = server_name[:27] + "..."
                
            draw.text(
                (rect_pad + 200, rect_pad + 160),
                f"auf {server_name}",
                fill=(180, 180, 180),
                font=subtitle_font
            )
            
            # Server member count
            draw.text(
                (rect_pad + rect_width - 20, rect_pad + rect_height - 20),
                f"Mitglied #{user.guild.member_count}",
                fill=(150, 150, 150),
                font=cls._get_font(20),
                anchor="rb"  # Right-bottom aligned
            )
            
            # Convert the PIL image to bytes
            buffer = io.BytesIO()
            image.save(buffer, 'PNG')
            buffer.seek(0)
            
            # Create a Discord file from the buffer
            return discord.File(buffer, filename=f"welcome_{user.id}.png")
            
        except Exception as e:
            logger.error(f"Error creating welcome image: {e}")
            return None