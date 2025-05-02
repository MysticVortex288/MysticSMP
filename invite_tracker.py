import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Dict, Optional, List, Union

from utils.config_manager import ConfigManager
from utils.embed_creator import EmbedCreator

logger = logging.getLogger('discord_bot')

class InviteTracker(commands.Cog):
    """Cog for tracking server invites and who invited whom."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_manager = ConfigManager()
        self.embed_creator = EmbedCreator()
        self.invite_cache: Dict[int, Dict[str, discord.Invite]] = {}
        
    async def cog_load(self):
        """Called when the cog is loaded."""
        # Initialize invite cache for all guilds the bot is in
        for guild in self.bot.guilds:
            try:
                await self._update_invite_cache(guild)
            except Exception as e:
                logger.error(f"Failed to initialize invite cache for guild {guild.name} (ID: {guild.id}): {e}")
    
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Event triggered when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        await self._update_invite_cache(guild)
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Event triggered when the bot leaves a guild."""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        if guild.id in self.invite_cache:
            del self.invite_cache[guild.id]
    
    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        """Event triggered when a new invite is created."""
        logger.debug(f"New invite created: {invite.code} in guild {invite.guild.name}")
        
        # Update the invite cache for the guild
        if invite.guild.id not in self.invite_cache:
            self.invite_cache[invite.guild.id] = {}
            
        self.invite_cache[invite.guild.id][invite.code] = invite
        
        # Save invite data to persistent storage
        self.config_manager.update_invite_data(
            invite.guild.id, 
            invite.code, 
            {
                "inviter_id": invite.inviter.id if invite.inviter else None,
                "uses": invite.uses,
                "max_uses": invite.max_uses,
                "created_at": invite.created_at.isoformat() if invite.created_at else None
            }
        )
    
    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        """Event triggered when an invite is deleted."""
        logger.debug(f"Invite deleted: {invite.code} in guild {invite.guild.name}")
        
        # Update the invite cache
        if invite.guild.id in self.invite_cache:
            if invite.code in self.invite_cache[invite.guild.id]:
                del self.invite_cache[invite.guild.id][invite.code]
                
        # Remove from persistent storage
        self.config_manager.remove_invite_data(invite.guild.id, invite.code)
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Event triggered when a new member joins a guild."""
        logger.info(f"Member joined: {member.name} (ID: {member.id}) in guild {member.guild.name}")
        
        # Skip if the member is a bot
        if member.bot:
            logger.debug(f"Skipping invite tracking for bot: {member.name}")
            return
            
        # Find out who invited the member
        inviter = await self._find_used_invite(member.guild)
        
        if inviter:
            logger.info(f"Member {member.name} was invited by {inviter.name if hasattr(inviter, 'name') else 'Unknown'}")
        else:
            logger.info(f"Could not determine who invited {member.name}")
    
    async def _update_invite_cache(self, guild: discord.Guild):
        """Update the invite cache for a specific guild."""
        try:
            # Check if the bot has permissions to manage guild or view audit log
            if not guild.me.guild_permissions.manage_guild and not guild.me.guild_permissions.view_audit_log:
                logger.warning(f"Insufficient permissions to fetch invites in guild {guild.name} (ID: {guild.id})")
                return
                
            # Fetch all current invites
            invites = await guild.invites()
            
            # Initialize cache for this guild if not exists
            if guild.id not in self.invite_cache:
                self.invite_cache[guild.id] = {}
                
            # Update the cache
            for invite in invites:
                self.invite_cache[guild.id][invite.code] = invite
                
                # Also update the persistent storage
                self.config_manager.update_invite_data(
                    guild.id, 
                    invite.code, 
                    {
                        "inviter_id": invite.inviter.id if invite.inviter else None,
                        "uses": invite.uses,
                        "max_uses": invite.max_uses,
                        "created_at": invite.created_at.isoformat() if invite.created_at else None
                    }
                )
                
            logger.debug(f"Updated invite cache for guild {guild.name} (ID: {guild.id}): {len(invites)} invites")
        except discord.Forbidden:
            logger.warning(f"Bot doesn't have permission to fetch invites in guild {guild.name} (ID: {guild.id})")
        except Exception as e:
            logger.error(f"Error updating invite cache for guild {guild.name} (ID: {guild.id}): {e}")
    
    async def _find_used_invite(self, guild: discord.Guild) -> Optional[discord.Member]:
        """
        Determine which invite was used when a member joined.
        
        Args:
            guild: The discord Guild the member joined
            
        Returns:
            Optional[discord.Member]: The member who created the invite, or None
        """
        # Store old invite counts
        old_invites = self.invite_cache.get(guild.id, {}).copy()
        
        # Update invite cache to get new invite counts
        await self._update_invite_cache(guild)
        new_invites = self.invite_cache.get(guild.id, {})
        
        # Compare invite counts to find the one that was used
        for invite_code, invite in new_invites.items():
            # If this is a new invite that we haven't seen before
            if invite_code not in old_invites:
                if invite.uses > 0:
                    if invite.inviter:
                        return guild.get_member(invite.inviter.id) or invite.inviter
                    return None
                continue
                
            # If the invite uses have increased
            if invite.uses > old_invites[invite_code].uses:
                if invite.inviter:
                    return guild.get_member(invite.inviter.id) or invite.inviter
                return None
                
        # Could not determine the used invite
        return None
    
    @commands.hybrid_command(name="invites", description="Show how many people you have invited to the server")
    @app_commands.describe(member="The member to check invites for (optional)")
    async def invites(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        """
        Show invite statistics for a member or yourself.
        """
        target = member or ctx.author
        
        # Fetch all invites for the guild
        try:
            invites = await ctx.guild.invites()
        except discord.Forbidden:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Missing Permissions",
                "I don't have permission to view invites in this server."
            ))
            return
            
        # Count invites for the target user
        invite_count = 0
        for invite in invites:
            if invite.inviter and invite.inviter.id == target.id:
                invite_count += invite.uses
                
        # Create and send the embed
        embed = discord.Embed(
            title=f"Invite Stats for {target.display_name}",
            description=f"{target.mention} has invited **{invite_count}** member(s) to the server.",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.timestamp = discord.utils.utcnow()
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="invite-leaderboard", aliases=["inviteleaderboard", "invitelb"], description="Show the invite leaderboard for the server")
    async def invite_leaderboard(self, ctx: commands.Context):
        """
        Display a leaderboard of members with the most invites.
        """
        # Fetch all invites for the guild
        try:
            invites = await ctx.guild.invites()
        except discord.Forbidden:
            await ctx.send(embed=self.embed_creator.create_error_embed(
                "Missing Permissions",
                "I don't have permission to view invites in this server."
            ))
            return
            
        # Count invites per user
        invite_counts = {}
        for invite in invites:
            if invite.inviter:
                if invite.inviter.id not in invite_counts:
                    invite_counts[invite.inviter.id] = 0
                invite_counts[invite.inviter.id] += invite.uses
                
        # Sort users by invite count
        sorted_invites = sorted(invite_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Create the embed
        embed = discord.Embed(
            title=f"Invite Leaderboard - {ctx.guild.name}",
            color=discord.Color.blue()
        )
        
        # Add top 10 inviters to the embed
        description = ""
        for index, (user_id, count) in enumerate(sorted_invites[:10], start=1):
            member = ctx.guild.get_member(user_id)
            name = member.display_name if member else f"Unknown User ({user_id})"
            description += f"{index}. **{name}** - {count} invite{'s' if count != 1 else ''}\n"
            
        if not description:
            description = "No invites have been tracked yet."
            
        embed.description = description
        embed.timestamp = discord.utils.utcnow()
        embed.set_footer(text=f"Requested by {ctx.author}")
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """Add the InviteTracker cog to the bot."""
    await bot.add_cog(InviteTracker(bot))
    logger.info("InviteTracker cog loaded")
