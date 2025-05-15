import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger('discord_bot')

class XPView(discord.ui.View):
    def __init__(self, user_data, level_data):
        super().__init__(timeout=60)
        self.user_data = user_data
        self.level_data = level_data
        
    @discord.ui.button(label="Zeige meine XP", style=discord.ButtonStyle.primary)
    async def show_xp(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to show user's XP details"""
        if str(interaction.user.id) in self.user_data:
            user_xp = self.user_data[str(interaction.user.id)]
            current_level = user_xp["level"]
            current_xp = user_xp["xp"]
            
            # Calculate XP needed for next level
            xp_needed = LevelSystem.calculate_xp_for_level(current_level + 1)
            
            embed = discord.Embed(
                title=f"{interaction.user.display_name}'s Level-Statistik",
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.add_field(name="Level", value=str(current_level), inline=True)
            embed.add_field(name="XP", value=f"{current_xp}/{xp_needed}", inline=True)
            embed.add_field(name="Rang", value=self._get_rank(interaction.user.id), inline=True)
            
            # Progress bar (15 segments)
            progress = min(int((current_xp / xp_needed) * 15), 15)
            progress_bar = "▰" * progress + "▱" * (15 - progress)
            embed.add_field(name="Fortschritt", value=progress_bar, inline=False)
            
            # Show next role
            next_level_role = self._get_next_role(current_level, interaction.guild)
            if next_level_role:
                embed.add_field(name="Nächste Rolle", value=f"Level {next_level_role[0]}: {next_level_role[1]}", inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("Du hast noch keine XP gesammelt. Schreibe Nachrichten, um zu beginnen!", ephemeral=True)
    
    def _get_rank(self, user_id):
        # Sort users by XP and find the rank of the current user
        sorted_users = sorted(self.user_data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)
        for i, (uid, _) in enumerate(sorted_users):
            if int(uid) == user_id:
                return f"#{i+1}"
        return "N/A"
    
    def _get_next_role(self, current_level, guild):
        # Find the next role milestone
        for level, role_name in sorted(self.level_data["roles"].items()):
            if int(level) > current_level:
                return (level, role_name)
        return None

class LevelSystem(commands.Cog):
    """Cog for the level and experience system."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "levels.json"
        self.xp_cooldowns = {}  # To prevent spam
        self.level_data = self._load_level_data()
        self.leaderboard_channel_id = None
        self.leaderboard_message_id = None
        # Load channel and message IDs if available
        if "leaderboard_channel" in self.level_data and "leaderboard_message" in self.level_data:
            self.leaderboard_channel_id = self.level_data["leaderboard_channel"]
            self.leaderboard_message_id = self.level_data["leaderboard_message"]
        logger.info("LevelSystem cog initialized")
        
    def _load_level_data(self):
        """Load the level data from file."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create default level data
            default_data = {
                "users": {},
                "roles": {
                    "1": "ChatRevive",
                    "5": "Rookie",
                    "10": "Amateur",
                    "15": "Regular",
                    "25": "Veteran",
                    "40": "Master",
                    "60": "Legend"
                },
                "xp_per_message": {
                    "min": 15,
                    "max": 25
                }
            }
            self._save_level_data(default_data)
            return default_data
    
    def _save_level_data(self, data=None):
        """Save the level data to file."""
        if data is None:
            data = self.level_data
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=4)
    
    @staticmethod
    def calculate_xp_for_level(level):
        """Calculate how much XP is needed for a specific level."""
        # This formula makes leveling progressively harder
        return 100 * level * level
    
    async def _award_role(self, member, level):
        """Award role based on level."""
        # Get all role milestones that apply to this level
        applicable_roles = {}
        for level_req, role_name in self.level_data["roles"].items():
            if int(level) >= int(level_req):
                applicable_roles[int(level_req)] = role_name
        
        if not applicable_roles:
            return
        
        # Get the highest applicable role
        highest_level = max(applicable_roles.keys())
        role_name = applicable_roles[highest_level]
        
        # Check if role exists, create if not
        role = discord.utils.get(member.guild.roles, name=role_name)
        if not role:
            # Create role with same permissions as @everyone
            everyone_role = member.guild.default_role
            try:
                role = await member.guild.create_role(
                    name=role_name,
                    permissions=everyone_role.permissions,
                    color=discord.Color.random(),
                    reason="Level system role"
                )
                logger.info(f"Created role {role_name} for level {highest_level}")
            except discord.Forbidden:
                logger.error(f"Bot does not have permission to create roles")
                return
        
        # Add the role if user doesn't have it
        if role not in member.roles:
            try:
                await member.add_roles(role, reason=f"Reached level {level}")
                logger.info(f"Added role {role_name} to {member.display_name}")
            except discord.Forbidden:
                logger.error(f"Bot does not have permission to add roles")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages to award XP."""
        # Don't give XP for bot messages or commands
        try:
            prefix = await self.bot.get_prefix(message)
            # Convert to string if it's a list
            if isinstance(prefix, list):
                prefix = prefix[0]
            
            if message.author.bot or message.content.startswith(prefix):
                return
        except Exception as e:
            logger.error(f"Error checking prefix: {e}")
            # Fallback: just check if author is a bot
            if message.author.bot:
                return
        
        # Check cooldown (to prevent spam for XP)
        user_id = str(message.author.id)
        if user_id in self.xp_cooldowns:
            if datetime.now() < self.xp_cooldowns[user_id]:
                return
        
        # Set cooldown (60 seconds)
        self.xp_cooldowns[user_id] = datetime.now() + timedelta(seconds=60)
        
        # Get current user data
        user_data = self.level_data["users"].get(user_id, {"level": 0, "xp": 0})
        
        # Generate random XP between min and max
        xp_range = self.level_data["xp_per_message"]
        earned_xp = random.randint(xp_range["min"], xp_range["max"])
        
        # Add XP
        user_data["xp"] += earned_xp
        
        # Check if level up
        current_level = user_data["level"]
        xp_needed = self.calculate_xp_for_level(current_level + 1)
        
        if user_data["xp"] >= xp_needed:
            # Level up!
            user_data["level"] += 1
            user_data["xp"] -= xp_needed  # Reset XP counter for next level
            
            # Send level up message
            embed = discord.Embed(
                title="Level aufgestiegen! 🎉",
                description=f"{message.author.mention} ist auf **Level {user_data['level']}** aufgestiegen!",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            await message.channel.send(embed=embed)
            
            # Award role if applicable
            await self._award_role(message.author, user_data["level"])
        
        # Save updated user data
        self.level_data["users"][user_id] = user_data
        self._save_level_data()
    
    @commands.hybrid_command(name="setuplevel")
    @commands.has_permissions(administrator=True)
    async def setup_level(self, ctx: commands.Context):
        """Einrichtung des Level-Systems"""
        embed = discord.Embed(
            title="Level-System Einrichtung",
            description="Das Level-System wurde erfolgreich eingerichtet!",
            color=discord.Color.blue()
        )
        
        # Add field for role information
        roles_text = "\n".join(f"Level {level}: {role}" for level, role in self.level_data["roles"].items())
        embed.add_field(name="Rollen", value=roles_text, inline=False)
        
        # Add field for XP information
        xp_info = f"XP pro Nachricht: {self.level_data['xp_per_message']['min']}-{self.level_data['xp_per_message']['max']}"
        embed.add_field(name="XP-Informationen", value=xp_info, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="leaderboard", aliases=["lb", "levels", "ranking"])
    async def leaderboard(self, ctx: commands.Context):
        """Zeigt die Top-10 Nutzer mit dem höchsten Level."""
        # Sort users by level and XP
        sorted_users = sorted(
            self.level_data["users"].items(),
            key=lambda x: (x[1]["level"], x[1]["xp"]),
            reverse=True
        )[:10]  # Get top 10
        
        if not sorted_users:
            await ctx.send("Noch niemand hat XP gesammelt!")
            return
        
        embed = discord.Embed(
            title="Level-Rangliste",
            description="Die aktivsten Mitglieder des Servers",
            color=discord.Color.gold()
        )
        
        for i, (user_id, data) in enumerate(sorted_users):
            member = ctx.guild.get_member(int(user_id))
            if member:
                name = member.display_name
                # Show progress to next level
                next_level_xp = self.calculate_xp_for_level(data["level"] + 1)
                progress = f"{data['xp']}/{next_level_xp} XP"
                
                # Medals for top 3
                medal = ""
                if i == 0:
                    medal = "🥇 "
                elif i == 1:
                    medal = "🥈 "
                elif i == 2:
                    medal = "🥉 "
                else:
                    medal = f"#{i+1} "
                
                embed.add_field(
                    name=f"{medal}{name}",
                    value=f"Level {data['level']} • {progress}",
                    inline=False
                )
        
        # Add a button for users to check their own XP
        view = XPView(self.level_data["users"], self.level_data)
        await ctx.send(embed=embed, view=view)
    
    @commands.hybrid_command(name="rank")
    async def rank(self, ctx: commands.Context, member: discord.Member = None):
        """Zeigt den Rang und XP-Fortschritt eines Nutzers."""
        # If no member specified, use the command invoker
        if member is None:
            member = ctx.author
        
        user_id = str(member.id)
        
        if user_id not in self.level_data["users"]:
            await ctx.send(f"{member.display_name} hat noch keine XP gesammelt.")
            return
        
        user_data = self.level_data["users"][user_id]
        current_level = user_data["level"]
        current_xp = user_data["xp"]
        
        # Calculate XP needed for next level
        xp_needed = self.calculate_xp_for_level(current_level + 1)
        
        # Get rank
        sorted_users = sorted(
            self.level_data["users"].items(),
            key=lambda x: (x[1]["level"], x[1]["xp"]),
            reverse=True
        )
        rank = "N/A"
        for i, (uid, _) in enumerate(sorted_users):
            if uid == user_id:
                rank = i + 1
                break
        
        embed = discord.Embed(
            title=f"{member.display_name}'s Level-Statistik",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Rang", value=f"#{rank}", inline=True)
        embed.add_field(name="Level", value=str(current_level), inline=True)
        embed.add_field(name="XP", value=f"{current_xp}/{xp_needed}", inline=True)
        
        # Progress bar (15 segments)
        progress = min(int((current_xp / xp_needed) * 15), 15)
        progress_bar = "▰" * progress + "▱" * (15 - progress)
        embed.add_field(name="Fortschritt", value=progress_bar, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="setlevelrole")
    @commands.has_permissions(administrator=True)
    async def set_level_role(self, ctx: commands.Context, level: int, *, role_name: str):
        """Legt eine Rolle fest, die bei Erreichen eines bestimmten Levels vergeben wird."""
        if level < 1:
            await ctx.send("Das Level muss mindestens 1 sein.")
            return
        
        self.level_data["roles"][str(level)] = role_name
        self._save_level_data()
        
        await ctx.send(f"Die Rolle '{role_name}' wird jetzt bei Level {level} vergeben.")
    
    @commands.hybrid_command(name="setxprange")
    @commands.has_permissions(administrator=True)
    async def set_xp_range(self, ctx: commands.Context, min_xp: int, max_xp: int):
        """Legt den Bereich der XP fest, die pro Nachricht vergeben werden."""
        if min_xp < 1 or max_xp < min_xp:
            await ctx.send("Der minimale XP-Wert muss mindestens 1 sein und der maximale Wert muss größer oder gleich dem minimalen sein.")
            return
        
        self.level_data["xp_per_message"]["min"] = min_xp
        self.level_data["xp_per_message"]["max"] = max_xp
        self._save_level_data()
        
        await ctx.send(f"Nutzer erhalten jetzt {min_xp}-{max_xp} XP pro Nachricht.")

    @commands.hybrid_command(name="setleaderboardchannel")
    @commands.has_permissions(administrator=True)
    async def set_leaderboard_channel(self, ctx: commands.Context):
        """Legt den aktuellen Kanal als automatisch aktualisierenden Leaderboard-Kanal fest."""
        self.leaderboard_channel_id = ctx.channel.id
        self.leaderboard_message_id = None  # Reset message ID as we'll create a new one
        
        # Create initial leaderboard message
        embed, view = await self._create_leaderboard_embed(ctx.guild)
        if embed:
            message = await ctx.send("Leaderboard wird in diesem Kanal automatisch aktualisiert:", embed=embed, view=view)
            self.leaderboard_message_id = message.id
            
            # Save these settings to the level data
            self.level_data["leaderboard_channel"] = self.leaderboard_channel_id
            self.level_data["leaderboard_message"] = self.leaderboard_message_id
            self._save_level_data()
            
            await ctx.send("Leaderboard-Kanal erfolgreich festgelegt!", delete_after=5)
        else:
            await ctx.send("Es konnten keine Benutzer für das Leaderboard gefunden werden. Versuche es später erneut.")
    
    async def _create_leaderboard_embed(self, guild):
        """Create a leaderboard embed with the top 10 users."""
        # Sort users by level and XP
        sorted_users = sorted(
            self.level_data["users"].items(),
            key=lambda x: (x[1]["level"], x[1]["xp"]),
            reverse=True
        )[:10]  # Get top 10
        
        if not sorted_users:
            return None, None
        
        embed = discord.Embed(
            title="Level-Rangliste 🏆",
            description="Die aktivsten Mitglieder des Servers\n(Aktualisiert sich automatisch alle 5 Minuten)",
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        for i, (user_id, data) in enumerate(sorted_users):
            member = guild.get_member(int(user_id))
            if member:
                name = member.display_name
                # Show progress to next level
                next_level_xp = self.calculate_xp_for_level(data["level"] + 1)
                progress = f"{data['xp']}/{next_level_xp} XP"
                
                # Medals for top 3
                medal = ""
                if i == 0:
                    medal = "🥇 "
                elif i == 1:
                    medal = "🥈 "
                elif i == 2:
                    medal = "🥉 "
                else:
                    medal = f"#{i+1} "
                
                embed.add_field(
                    name=f"{medal}{name}",
                    value=f"Level {data['level']} • {progress}",
                    inline=False
                )
        
        # Add footer with timestamp
        embed.set_footer(text="Letzte Aktualisierung")
        
        # Create view with button
        view = XPView(self.level_data["users"], self.level_data)
        
        return embed, view
    
    async def update_leaderboard(self):
        """Update the leaderboard message."""
        # Load channel and message IDs from level data if they exist
        if "leaderboard_channel" in self.level_data and "leaderboard_message" in self.level_data:
            self.leaderboard_channel_id = self.level_data["leaderboard_channel"]
            self.leaderboard_message_id = self.level_data["leaderboard_message"]
        
        # Check if we have a leaderboard channel and message set
        if not self.leaderboard_channel_id or not self.leaderboard_message_id:
            return
        
        try:
            # Get the channel and message
            channel = self.bot.get_channel(self.leaderboard_channel_id)
            if not channel:
                logger.error(f"Could not find leaderboard channel with ID {self.leaderboard_channel_id}")
                return
            
            try:
                message = await channel.fetch_message(self.leaderboard_message_id)
                
                # Create updated embed and view
                embed, view = await self._create_leaderboard_embed(channel.guild)
                if embed:
                    await message.edit(embed=embed, view=view)
                    logger.info(f"Updated leaderboard message in channel {channel.name}")
            except discord.NotFound:
                # Message was deleted, create a new one
                logger.info("Leaderboard message was deleted, creating a new one")
                embed, view = await self._create_leaderboard_embed(channel.guild)
                if embed:
                    new_message = await channel.send("Leaderboard wird in diesem Kanal automatisch aktualisiert:", embed=embed, view=view)
                    self.leaderboard_message_id = new_message.id
                    self.level_data["leaderboard_message"] = self.leaderboard_message_id
                    self._save_level_data()
        except Exception as e:
            logger.error(f"Error updating leaderboard: {e}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages to award XP and update leaderboard."""
        # Process XP
        await self._process_xp(message)
        
        # Update leaderboard on certain interval
        current_time = datetime.now()
        last_update = self.level_data.get("last_leaderboard_update", 0)
        
        # Update leaderboard every 5 minutes (300 seconds)
        if isinstance(last_update, int) and (current_time.timestamp() - last_update > 300):
            await self.update_leaderboard()
            self.level_data["last_leaderboard_update"] = int(current_time.timestamp())
            self._save_level_data()
    
    async def _process_xp(self, message):
        """Process XP for a message."""
        # Don't give XP for bot messages or commands
        try:
            prefix = await self.bot.get_prefix(message)
            # Convert to string if it's a list
            if isinstance(prefix, list):
                prefix = prefix[0]
            
            if message.author.bot or message.content.startswith(prefix):
                return
        except Exception as e:
            logger.error(f"Error checking prefix: {e}")
            # Fallback: just check if author is a bot
            if message.author.bot:
                return
        
        # Check cooldown (to prevent spam for XP)
        user_id = str(message.author.id)
        if user_id in self.xp_cooldowns:
            if datetime.now() < self.xp_cooldowns[user_id]:
                return
        
        # Set cooldown (60 seconds)
        self.xp_cooldowns[user_id] = datetime.now() + timedelta(seconds=60)
        
        # Get current user data
        user_data = self.level_data["users"].get(user_id, {"level": 0, "xp": 0})
        
        # Generate random XP between min and max
        xp_range = self.level_data["xp_per_message"]
        earned_xp = random.randint(xp_range["min"], xp_range["max"])
        
        # Add XP
        user_data["xp"] += earned_xp
        
        # Check if level up
        current_level = user_data["level"]
        xp_needed = self.calculate_xp_for_level(current_level + 1)
        
        if user_data["xp"] >= xp_needed:
            # Level up!
            user_data["level"] += 1
            user_data["xp"] -= xp_needed  # Reset XP counter for next level
            
            # Send level up message
            embed = discord.Embed(
                title="Level aufgestiegen! 🎉",
                description=f"{message.author.mention} ist auf **Level {user_data['level']}** aufgestiegen!",
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            await message.channel.send(embed=embed)
            
            # Award role if applicable
            await self._award_role(message.author, user_data["level"])
        
        # Save updated user data
        self.level_data["users"][user_id] = user_data
        self._save_level_data()

async def setup(bot: commands.Bot):
    """Add the LevelSystem cog to the bot."""
    await bot.add_cog(LevelSystem(bot))
    logger.info("LevelSystem cog loaded")