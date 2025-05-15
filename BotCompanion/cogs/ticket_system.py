import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger('discord_bot')

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view that doesn't timeout
        
    @discord.ui.button(label="Ticket erstellen", style=discord.ButtonStyle.primary, emoji="🎫", custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to create a new support ticket"""
        # Check if the user already has an open ticket
        ticket_manager = interaction.client.get_cog("TicketSystem")
        if await ticket_manager.user_has_ticket(interaction.guild, interaction.user):
            await interaction.response.send_message("Du hast bereits ein offenes Ticket. Bitte schließe dieses zuerst.", ephemeral=True)
            return
        
        await ticket_manager.create_ticket(interaction)

class TicketSystem(commands.Cog):
    """Cog for handling support tickets."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "tickets.json"
        self.ticket_data = self._load_ticket_data()
        self.ticket_counter = self.ticket_data.get("counter", 0)
        
        # Add the persistent view for ticket buttons
        self.bot.add_view(TicketView())
        
        logger.info("TicketSystem cog initialized")
        
    def _load_ticket_data(self):
        """Load the ticket data from file."""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                
                # Stellen sicher, dass die erforderlichen Schlüssel in den Einstellungen vorhanden sind
                if "settings" not in data:
                    data["settings"] = {}
                
                if "support_role_ids" not in data["settings"]:
                    data["settings"]["support_role_ids"] = []
                    # Wenn es eine alte support_role_id gibt, migrieren wir sie
                    if "support_role_id" in data["settings"] and data["settings"]["support_role_id"]:
                        data["settings"]["support_role_ids"].append(data["settings"]["support_role_id"])
                
                if "category_id" not in data["settings"]:
                    data["settings"]["category_id"] = None
                
                if "log_channel_id" not in data["settings"]:
                    data["settings"]["log_channel_id"] = None
                
                if "ticket_message" not in data["settings"]:
                    data["settings"]["ticket_message"] = "Willkommen bei deinem Support-Ticket!\n\nBitte beschreibe dein Anliegen so detailliert wie möglich, und ein Teammitglied wird sich so schnell wie möglich bei dir melden."
                
                # Speichern der aktualisierten Daten
                self._save_ticket_data(data)
                return data
                
        except FileNotFoundError:
            # Create default ticket data
            default_data = {
                "counter": 0,
                "tickets": {},
                "settings": {
                    "category_id": None,
                    "support_role_ids": [],
                    "log_channel_id": None,
                    "ticket_message": "Willkommen bei deinem Support-Ticket!\n\nBitte beschreibe dein Anliegen so detailliert wie möglich, und ein Teammitglied wird sich so schnell wie möglich bei dir melden."
                }
            }
            self._save_ticket_data(default_data)
            return default_data
    
    def _save_ticket_data(self, data=None):
        """Save the ticket data to file."""
        if data is None:
            data = self.ticket_data
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=4)
    
    @commands.hybrid_command(name="setupticket", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def setup_ticket(self, ctx: commands.Context, category: discord.CategoryChannel = None, 
                         support_role: discord.Role = None):
        """
        Richtet das Ticket-System ein.
        
        Args:
            category: Die Kategorie, in der die Tickets erstellt werden sollen
            support_role: Die erste Rolle für Support-Mitarbeiter
        """
        # Versuchen, das Ticket-System einzurichten
        try:
            # Kategorie speichern, wenn angegeben
            if category:
                self.ticket_data["settings"]["category_id"] = category.id
            
            # Sicherstellen, dass support_role_ids existiert
            if "support_role_ids" not in self.ticket_data["settings"]:
                self.ticket_data["settings"]["support_role_ids"] = []
            
            # Legacy support_role_id migrieren, falls vorhanden
            if "support_role_id" in self.ticket_data["settings"] and self.ticket_data["settings"]["support_role_id"]:
                old_role_id = self.ticket_data["settings"]["support_role_id"]
                if old_role_id not in self.ticket_data["settings"]["support_role_ids"]:
                    self.ticket_data["settings"]["support_role_ids"].append(old_role_id)
            
            # Neue Support-Rolle hinzufügen, falls angegeben
            if support_role and support_role.id not in self.ticket_data["settings"]["support_role_ids"]:
                self.ticket_data["settings"]["support_role_ids"].append(support_role.id)
            
            # Änderungen speichern
            self._save_ticket_data()
            
            # Antwort erstellen
            support_roles = []
            for role_id in self.ticket_data["settings"]["support_role_ids"]:
                role = ctx.guild.get_role(role_id)
                if role:
                    support_roles.append(role)
            
            embed = discord.Embed(
                title="Ticket-System Einrichtung",
                description="Das Ticket-System wurde erfolgreich eingerichtet!",
                color=discord.Color.blue()
            )
            
            if category:
                embed.add_field(name="Ticket-Kategorie", value=category.name, inline=False)
            else:
                embed.add_field(name="Ticket-Kategorie", value="Nicht festgelegt", inline=False)
            
            if support_roles:
                roles_text = ", ".join([role.mention for role in support_roles])
                embed.add_field(name="Support-Rollen", value=roles_text, inline=False)
            else:
                embed.add_field(name="Support-Rollen", value="Keine festgelegt", inline=False)
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in setupticket: {e}")
            await ctx.send(f"Fehler bei der Einrichtung des Ticket-Systems: {e}")
    
    @commands.hybrid_command(name="ticketpanel", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def ticket_panel(self, ctx: commands.Context, *, message: str = None):
        """
        Erstellt ein Ticket-Panel mit Button zum Erstellen von Tickets.
        
        Args:
            message: Optional angepasste Nachricht für das Panel
        """
        # Create embed for the ticket panel
        embed = discord.Embed(
            title="Support-Tickets",
            description=message or "Klicke auf den Button unten, um ein Support-Ticket zu erstellen.",
            color=discord.Color.blue()
        )
        
        # Add timestamp and footer
        embed.timestamp = datetime.now()
        embed.set_footer(text=f"{ctx.guild.name} | Support-System")
        
        # Send the panel with the ticket button
        await ctx.send(embed=embed, view=TicketView())
        
        # Delete the command message if possible
        try:
            await ctx.message.delete()
        except:
            pass
    
    @commands.hybrid_command(name="closeticket")
    async def close_ticket(self, ctx: commands.Context):
        """Schließt das aktuelle Ticket, wenn es eines ist."""
        # Check if the channel is a ticket
        channel_id = str(ctx.channel.id)
        if channel_id not in self.ticket_data["tickets"]:
            await ctx.send("Dieser Kanal ist kein Ticket.")
            return
        
        # Check permissions
        ticket_owner_id = int(self.ticket_data["tickets"][channel_id]["user_id"])
        is_staff = False
        
        if ctx.author.guild_permissions.administrator:
            is_staff = True
        else:
            # Prüfen, ob der Benutzer eine Support-Rolle hat
            for role_id in self.ticket_data["settings"]["support_role_ids"]:
                support_role = ctx.guild.get_role(role_id)
                if support_role and support_role in ctx.author.roles:
                    is_staff = True
                    break
            
            # Legacy-Kompatibilität
            if not is_staff and "support_role_id" in self.ticket_data["settings"] and self.ticket_data["settings"]["support_role_id"]:
                support_role = ctx.guild.get_role(self.ticket_data["settings"]["support_role_id"])
                if support_role and support_role in ctx.author.roles:
                    is_staff = True
        
        if ctx.author.id != ticket_owner_id and not is_staff:
            await ctx.send("Du hast keine Berechtigung, dieses Ticket zu schließen.")
            return
        
        # Confirm with a message
        embed = discord.Embed(
            title="Ticket wird geschlossen",
            description="Das Ticket wird in 5 Sekunden geschlossen...",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        
        # Wait 5 seconds
        await asyncio.sleep(5)
        
        # Delete the channel
        try:
            await ctx.channel.delete(reason=f"Ticket geschlossen von {ctx.author}")
            # Speichern der Ticketnummer vor dem Löschen
            ticket_number = self.ticket_data["tickets"][channel_id]["number"]
            
            # Remove from ticket data
            del self.ticket_data["tickets"][channel_id]
            self._save_ticket_data()
            
            # Log the ticket closure if log channel is set
            await self._log_action(ctx.guild, f"Ticket #{ticket_number} wurde von {ctx.author.mention} geschlossen.")
        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
    
    @commands.hybrid_command(name="addtoticket", default_permission=False)
    @commands.has_permissions(manage_channels=True)
    @app_commands.default_permissions(administrator=True)
    async def add_to_ticket(self, ctx: commands.Context, user: discord.Member):
        """
        Fügt einen Benutzer zu einem Ticket hinzu.
        
        Args:
            user: Der Benutzer, der zum Ticket hinzugefügt werden soll
        """
        # Check if the channel is a ticket
        channel_id = str(ctx.channel.id)
        if channel_id not in self.ticket_data["tickets"]:
            await ctx.send("Dieser Kanal ist kein Ticket.")
            return
        
        # Add user to the ticket
        try:
            await ctx.channel.set_permissions(user, read_messages=True, send_messages=True)
            await ctx.send(f"{user.mention} wurde zum Ticket hinzugefügt.")
        except Exception as e:
            logger.error(f"Error adding user to ticket: {e}")
            await ctx.send(f"Fehler beim Hinzufügen des Benutzers: {e}")
    
    @commands.hybrid_command(name="setticketmessage", default_permission=False)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def set_ticket_message(self, ctx: commands.Context, *, message: str):
        """
        Legt die Nachricht fest, die beim Erstellen eines Tickets angezeigt wird.
        
        Args:
            message: Die Nachricht, die angezeigt werden soll
        """
        self.ticket_data["settings"]["ticket_message"] = message
        self._save_ticket_data()
        
        embed = discord.Embed(
            title="Ticket-Nachricht aktualisiert",
            description="Die Ticket-Nachricht wurde erfolgreich aktualisiert.",
            color=discord.Color.green()
        )
        embed.add_field(name="Neue Nachricht", value=message, inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="setlogchannel")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """
        Legt den Kanal fest, in dem Ticket-Aktionen protokolliert werden.
        
        Args:
            channel: Der Kanal für Ticket-Logs
        """
        self.ticket_data["settings"]["log_channel_id"] = channel.id
        self._save_ticket_data()
        
        embed = discord.Embed(
            title="Log-Kanal aktualisiert",
            description=f"Der Log-Kanal wurde auf {channel.mention} festgelegt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
        
    @commands.hybrid_command(name="addsupportrole")
    @commands.has_permissions(administrator=True)
    async def add_support_role(self, ctx: commands.Context, role: discord.Role):
        """
        Fügt eine Rolle zur Liste der Support-Rollen hinzu, die Zugriff auf Tickets haben.
        
        Args:
            role: Die Rolle, die als Support-Rolle hinzugefügt werden soll
        """
        # Stelle sicher, dass der Schlüssel support_role_ids existiert
        if "support_role_ids" not in self.ticket_data["settings"]:
            self.ticket_data["settings"]["support_role_ids"] = []
            self._save_ticket_data()
            
        # Wenn die Rolle bereits in der Liste ist, nichts tun
        if role.id in self.ticket_data["settings"]["support_role_ids"]:
            await ctx.send(f"Die Rolle {role.mention} ist bereits als Support-Rolle eingerichtet.")
            return
        
        # Rolle hinzufügen
        self.ticket_data["settings"]["support_role_ids"].append(role.id)
        self._save_ticket_data()
        
        # Support-Rollen abrufen für die Anzeige
        support_roles = []
        for role_id in self.ticket_data["settings"]["support_role_ids"]:
            role = ctx.guild.get_role(role_id)
            if role:
                support_roles.append(role)
        
        embed = discord.Embed(
            title="Support-Rolle hinzugefügt",
            description=f"Die Rolle {role.mention} wurde als Support-Rolle hinzugefügt.",
            color=discord.Color.green()
        )
        
        if support_roles:
            roles_text = ", ".join([role.mention for role in support_roles])
            embed.add_field(name="Aktuelle Support-Rollen", value=roles_text, inline=False)
        
        await ctx.send(embed=embed)
        
    @commands.hybrid_command(name="removesupportrole")
    @commands.has_permissions(administrator=True)
    async def remove_support_role(self, ctx: commands.Context, role: discord.Role):
        """
        Entfernt eine Rolle aus der Liste der Support-Rollen.
        
        Args:
            role: Die Rolle, die als Support-Rolle entfernt werden soll
        """
        # Stelle sicher, dass der Schlüssel support_role_ids existiert
        if "support_role_ids" not in self.ticket_data["settings"]:
            self.ticket_data["settings"]["support_role_ids"] = []
            self._save_ticket_data()
            
        # Wenn die Rolle nicht in der Liste ist, nichts tun
        if role.id not in self.ticket_data["settings"]["support_role_ids"]:
            await ctx.send(f"Die Rolle {role.mention} ist keine Support-Rolle.")
            return
        
        # Rolle entfernen
        self.ticket_data["settings"]["support_role_ids"].remove(role.id)
        self._save_ticket_data()
        
        # Support-Rollen abrufen für die Anzeige
        support_roles = []
        for role_id in self.ticket_data["settings"]["support_role_ids"]:
            role = ctx.guild.get_role(role_id)
            if role:
                support_roles.append(role)
        
        embed = discord.Embed(
            title="Support-Rolle entfernt",
            description=f"Die Rolle {role.mention} wurde als Support-Rolle entfernt.",
            color=discord.Color.green()
        )
        
        if support_roles:
            roles_text = ", ".join([role.mention for role in support_roles])
            embed.add_field(name="Verbleibende Support-Rollen", value=roles_text, inline=False)
        else:
            embed.add_field(name="Verbleibende Support-Rollen", value="Keine Support-Rollen vorhanden.", inline=False)
        
        await ctx.send(embed=embed)
        
    @commands.hybrid_command(name="listsupportroles")
    @commands.has_permissions(administrator=True)
    async def list_support_roles(self, ctx: commands.Context):
        """
        Zeigt eine Liste aller Support-Rollen an, die Zugriff auf Tickets haben.
        """
        # Stelle sicher, dass der Schlüssel support_role_ids existiert
        if "support_role_ids" not in self.ticket_data["settings"]:
            self.ticket_data["settings"]["support_role_ids"] = []
            self._save_ticket_data()
        
        # Support-Rollen abrufen für die Anzeige
        support_roles = []
        for role_id in self.ticket_data["settings"]["support_role_ids"]:
            role = ctx.guild.get_role(role_id)
            if role:
                support_roles.append(role)
        
        embed = discord.Embed(
            title="Support-Rollen",
            description="Diese Rollen haben Zugriff auf Support-Tickets:",
            color=discord.Color.blue()
        )
        
        if support_roles:
            roles_text = "\n".join([f"• {role.mention}" for role in support_roles])
            embed.add_field(name="Aktuelle Support-Rollen", value=roles_text, inline=False)
        else:
            embed.add_field(name="Aktuelle Support-Rollen", value="Keine Support-Rollen vorhanden.", inline=False)
        
        await ctx.send(embed=embed)
    
    async def _log_action(self, guild, message):
        """Log an action to the log channel if one is set."""
        if not self.ticket_data["settings"]["log_channel_id"]:
            return
        
        log_channel = guild.get_channel(self.ticket_data["settings"]["log_channel_id"])
        if not log_channel:
            return
        
        embed = discord.Embed(
            description=message,
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.set_author(name="Ticket-Log")
        
        await log_channel.send(embed=embed)
    
    async def user_has_ticket(self, guild, user):
        """Check if a user already has an open ticket."""
        for ticket_id, ticket_info in self.ticket_data["tickets"].items():
            if ticket_info["user_id"] == user.id:
                channel = guild.get_channel(int(ticket_id))
                if channel:  # If channel still exists
                    return True
        return False
    
    async def create_ticket(self, interaction):
        """Create a new ticket for a user."""
        guild = interaction.guild
        user = interaction.user
        
        # Increment ticket counter
        self.ticket_counter += 1
        self.ticket_data["counter"] = self.ticket_counter
        
        # Create ticket channel name
        ticket_name = f"ticket-{self.ticket_counter}"
        
        # Get the category if set
        category = None
        if self.ticket_data["settings"]["category_id"]:
            category = guild.get_channel(self.ticket_data["settings"]["category_id"])
        
        # Create the ticket channel with permissions
        try:
            # Set permissions overwrites
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            # Stelle sicher, dass der Schlüssel support_role_ids existiert
            if "support_role_ids" not in self.ticket_data["settings"]:
                self.ticket_data["settings"]["support_role_ids"] = []
                self._save_ticket_data()
                
            # Add support role permissions for all configured roles
            for role_id in self.ticket_data["settings"]["support_role_ids"]:
                support_role = guild.get_role(role_id)
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
                    
            # Legacy-Kompatibilität
            if "support_role_id" in self.ticket_data["settings"] and self.ticket_data["settings"]["support_role_id"]:
                support_role = guild.get_role(self.ticket_data["settings"]["support_role_id"])
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
            # Create the channel
            ticket_channel = await guild.create_text_channel(
                name=ticket_name,
                category=category,
                overwrites=overwrites,
                reason=f"Support ticket for {user}"
            )
            
            # Store ticket info
            self.ticket_data["tickets"][str(ticket_channel.id)] = {
                "number": self.ticket_counter,
                "user_id": user.id,
                "created_at": int(datetime.now().timestamp())
            }
            self._save_ticket_data()
            
            # Send initial message
            embed = discord.Embed(
                title=f"Ticket #{self.ticket_counter}",
                description=self.ticket_data["settings"]["ticket_message"],
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="Erstellt von", value=user.mention, inline=True)
            
            # Add support role mentions if available
            support_mentions = []
            
            # Sammle Erwähnungen von allen konfigurierten Support-Rollen
            for role_id in self.ticket_data["settings"]["support_role_ids"]:
                support_role = guild.get_role(role_id)
                if support_role:
                    support_mentions.append(support_role.mention)
            
            # Legacy-Kompatibilität
            if "support_role_id" in self.ticket_data["settings"] and self.ticket_data["settings"]["support_role_id"]:
                support_role = guild.get_role(self.ticket_data["settings"]["support_role_id"])
                if support_role and support_role.mention not in support_mentions:
                    support_mentions.append(support_role.mention)
            
            # Füge Erwähnungen hinzu, wenn vorhanden
            if support_mentions:
                embed.add_field(name="Support", value=", ".join(support_mentions), inline=True)
            
            # Add close button
            close_button = discord.ui.Button(label="Ticket schließen", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_button")
            view = discord.ui.View()
            view.add_item(close_button)
            
            await ticket_channel.send(content=f"{user.mention}", embed=embed, view=view)
            
            # Respond to the interaction
            await interaction.response.send_message(f"Dein Ticket wurde erstellt: {ticket_channel.mention}", ephemeral=True)
            
            # Log the ticket creation
            await self._log_action(guild, f"Ticket #{self.ticket_counter} wurde von {user.mention} erstellt.")
            
        except Exception as e:
            logger.error(f"Error creating ticket: {e}")
            await interaction.response.send_message("Es gab einen Fehler beim Erstellen des Tickets. Bitte versuche es später erneut oder kontaktiere einen Administrator.", ephemeral=True)
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle button interactions."""
        if not interaction.data or not interaction.data.get("custom_id"):
            return
        
        custom_id = interaction.data["custom_id"]
        
        # Handle close ticket button
        if custom_id == "close_ticket_button":
            channel_id = str(interaction.channel_id)
            if channel_id not in self.ticket_data["tickets"]:
                await interaction.response.send_message("Dieser Kanal ist kein Ticket.", ephemeral=True)
                return
            
            # Check permissions
            ticket_owner_id = int(self.ticket_data["tickets"][channel_id]["user_id"])
            is_staff = False
            
            if interaction.user.guild_permissions.administrator:
                is_staff = True
            else:
                # Stelle sicher, dass der Schlüssel support_role_ids existiert
                if "support_role_ids" not in self.ticket_data["settings"]:
                    self.ticket_data["settings"]["support_role_ids"] = []
                    self._save_ticket_data()
                
                # Prüfen, ob der Benutzer eine Support-Rolle hat
                for role_id in self.ticket_data["settings"]["support_role_ids"]:
                    support_role = interaction.guild.get_role(role_id)
                    if support_role and support_role in interaction.user.roles:
                        is_staff = True
                        break
                
                # Legacy-Kompatibilität
                if not is_staff and "support_role_id" in self.ticket_data["settings"] and self.ticket_data["settings"]["support_role_id"]:
                    support_role = interaction.guild.get_role(self.ticket_data["settings"]["support_role_id"])
                    if support_role and support_role in interaction.user.roles:
                        is_staff = True
            
            if interaction.user.id != ticket_owner_id and not is_staff:
                await interaction.response.send_message("Du hast keine Berechtigung, dieses Ticket zu schließen.", ephemeral=True)
                return
            
            # Confirm with a message
            embed = discord.Embed(
                title="Ticket wird geschlossen",
                description="Das Ticket wird in 5 Sekunden geschlossen...",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            
            # Wait 5 seconds
            await asyncio.sleep(5)
            
            try:
                # Get ticket number before deleting
                ticket_number = self.ticket_data["tickets"][channel_id]["number"]
                
                # Delete the channel
                await interaction.channel.delete(reason=f"Ticket geschlossen von {interaction.user}")
                
                # Remove from ticket data
                del self.ticket_data["tickets"][channel_id]
                self._save_ticket_data()
                
                # Log the ticket closure
                await self._log_action(interaction.guild, f"Ticket #{ticket_number} wurde von {interaction.user.mention} geschlossen.")
            except Exception as e:
                logger.error(f"Error closing ticket: {e}")

async def setup(bot: commands.Bot):
    """Add the TicketSystem cog to the bot."""
    await bot.add_cog(TicketSystem(bot))
    logger.info("TicketSystem cog loaded")