import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger('discord_bot')

class VerifyButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)  # Damit der Button unbegrenzt funktioniert
        self.bot = bot
    
    @discord.ui.button(label="Verifizieren", style=discord.ButtonStyle.success, emoji="✅", custom_id="verify:button")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button zur Verifizierung von Nutzern"""
        try:
            # Suche nach der Member-Rolle
            member_role = None
            for role in interaction.guild.roles:
                if role.name.lower() == "member":
                    member_role = role
                    break
            
            # Erstelle die Rolle, wenn sie nicht existiert
            if not member_role:
                member_role = await interaction.guild.create_role(
                    name="Member",
                    colour=discord.Colour.green(),
                    reason="Automatisch erstellt für Verifizierungssystem"
                )
                logger.info(f"Created 'Member' role in guild {interaction.guild.name}")
            
            # Gib dem Nutzer die Rolle, wenn er sie noch nicht hat
            if member_role not in interaction.user.roles:
                await interaction.user.add_roles(member_role)
                await interaction.response.send_message("Du wurdest erfolgreich verifiziert! ✅", ephemeral=True)
                logger.info(f"User {interaction.user.name} verified and given 'Member' role")
            else:
                await interaction.response.send_message("Du bist bereits verifiziert!", ephemeral=True)
        
        except Exception as e:
            logger.error(f"Error during verification: {e}")
            await interaction.response.send_message("Bei der Verifizierung ist ein Fehler aufgetreten. Bitte kontaktiere einen Administrator.", ephemeral=True)

class Verification(commands.Cog):
    """Cog für das Verifizierungssystem."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Registriere den Verifizierungs-View beim Bot für persistente Views
        self.bot.add_view(VerifyButton(bot))
        
        logger.info("Verification cog initialized")
    
    @commands.hybrid_command(name="verify", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def verify(self, ctx: commands.Context, *, message: str = None):
        """
        Sendet eine Verifizierungsnachricht mit einem Button.
        
        Args:
            message: Optionale benutzerdefinierte Nachricht. Wenn nicht angegeben, wird der Standardtext verwendet.
        """
        try:
            # Standardnachricht, wenn keine angegeben wurde
            if not message:
                message = (
                    "**Willkommen auf unserem Server!**\n\n"
                    "Um Zugang zu allen Kanälen zu erhalten, musst du dich verifizieren.\n"
                    "Klicke auf den Button unten, um dich zu verifizieren und die Mitgliederrolle zu erhalten."
                )
            
            # Erstelle ein Embed für die Verifizierungsnachricht
            embed = discord.Embed(
                title="🔒 Verifizierung",
                description=message,
                color=discord.Color.blue()
            )
            
            embed.set_footer(text="Durch Klicken auf den Button unten erhältst du die Mitgliederrolle.")
            
            # Sende die Nachricht mit dem Verifizierungsbutton
            await ctx.send(embed=embed, view=VerifyButton(self.bot))
            
            # Lösche den Befehl des Nutzers, wenn möglich
            try:
                await ctx.message.delete()
            except:
                pass
            
            logger.info(f"Verification message sent in channel {ctx.channel.name}")
        
        except Exception as e:
            logger.error(f"Error sending verification message: {e}")
            await ctx.send(f"Fehler beim Senden der Verifizierungsnachricht: {e}")

    @commands.hybrid_command(name="setupverify", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def setup_verify(self, ctx: commands.Context, *, message: str = None):
        """
        Richtet das Verifizierungssystem ein und sendet eine Nachricht mit Verifizierungsbutton.
        
        Args:
            message: Optionale benutzerdefinierte Nachricht. Wenn nicht angegeben, wird der Standardtext verwendet.
        """
        try:
            # Prüfe, ob eine Member-Rolle existiert, sonst erstelle sie
            member_role = None
            for role in ctx.guild.roles:
                if role.name.lower() == "member":
                    member_role = role
                    break
            
            if not member_role:
                member_role = await ctx.guild.create_role(
                    name="Member",
                    colour=discord.Colour.green(),
                    reason="Erstellt für Verifizierungssystem"
                )
                logger.info(f"Created 'Member' role in guild {ctx.guild.name}")
            
            # Standardnachricht, wenn keine angegeben wurde
            if not message:
                message = (
                    "**Willkommen auf unserem Server!**\n\n"
                    "Um Zugang zu allen Kanälen zu erhalten, musst du dich verifizieren.\n"
                    "Klicke auf den Button unten, um dich zu verifizieren und die Mitgliederrolle zu erhalten."
                )
            
            # Erstelle ein Embed für die Verifizierungsnachricht
            embed = discord.Embed(
                title="🔒 Verifizierung",
                description=message,
                color=discord.Color.blue()
            )
            
            embed.set_footer(text="Durch Klicken auf den Button unten erhältst du die Mitgliederrolle.")
            
            # Sende die Nachricht mit dem Verifizierungsbutton
            await ctx.send(embed=embed, view=VerifyButton(self.bot))
            
            # Sende Bestätigungsnachricht
            confirm_embed = discord.Embed(
                title="✅ Verifizierungssystem eingerichtet",
                description=(
                    f"Das Verifizierungssystem wurde erfolgreich eingerichtet!\n\n"
                    f"Rolle: {member_role.mention}\n"
                    f"Neue Nutzer können den Verifizierungs-Button klicken, um die Rolle zu erhalten."
                ),
                color=discord.Color.green()
            )
            
            await ctx.send(embed=confirm_embed, ephemeral=True)
            
            logger.info(f"Verification system set up in guild {ctx.guild.name}")
        
        except Exception as e:
            logger.error(f"Error setting up verification system: {e}")
            await ctx.send(f"Fehler beim Einrichten des Verifizierungssystems: {e}")

async def setup(bot: commands.Bot):
    """Füge die Verification-Cog zum Bot hinzu."""
    await bot.add_cog(Verification(bot))
    logger.info("Verification cog loaded")