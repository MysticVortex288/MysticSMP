import discord
import json
import random
import logging
import asyncio
import datetime
from discord.ext import commands, tasks
from discord import app_commands
from typing import Optional, Dict, List, Union

logger = logging.getLogger('discord_bot')

class Economy(commands.Cog):
    """Cog für das Economy-System mit Credits und täglichen Belohnungen."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.economy_data = {}
        self.cooldowns = {}
        
        # Erweiterte Einstellungen für alle Economy-Befehle
        self.settings = {
            "global": {
                # Beg-Befehl Einstellungen
                "beg_chance": 0.7,      # 70% Chance für erfolgreichen Beg
                "beg_min": 5,           # Minimaler Betrag beim Beg
                "beg_max": 25,          # Maximaler Betrag beim Beg
                "beg_cooldown": 300,    # 5 Minuten Cooldown
                "beg_fail_loss": 0,     # 0 Credits Verlust bei Misserfolg
                
                # Work-Befehl Einstellungen
                "work_min": 10,         # Minimaler Betrag bei Arbeit
                "work_max": 100,        # Maximaler Betrag bei Arbeit
                "work_cooldown": 3600,  # 1 Stunde Cooldown
                
                # Daily-Befehl Einstellungen
                "daily_base": 100,      # Grundbetrag für tägliche Belohnung
                "daily_streak_bonus": 20, # Bonus pro Tag Streak
                "daily_max_streak": 7,  # Maximaler Streak für Bonus
                "daily_cooldown": 86400, # 24 Stunden Cooldown
                
                # Rob-Befehl Einstellungen
                "rob_chance": 0.4,      # 40% Chance für erfolgreichen Raub
                "rob_min_percent": 0.1, # Min. Prozent des Opfer-Guthabens
                "rob_max_percent": 0.3, # Max. Prozent des Opfer-Guthabens
                "rob_cooldown": 7200,   # 2 Stunden Cooldown
                "rob_fail_min": 10,     # Minimale Strafe bei Misserfolg
                "rob_fail_max": 50,     # Maximale Strafe bei Misserfolg
                
                # Pay-Befehl Einstellungen
                "pay_tax": 0.0,         # Steuer auf Überweisungen (0%)
                "pay_min": 1,           # Mindestüberweisungsbetrag
            }
        }
        
        self._load_economy_data()
        self.check_daily_reset.start()
        logger.info("Economy cog initialized")

    async def cog_unload(self):
        """Wird aufgerufen, wenn der Cog entladen wird."""
        self.check_daily_reset.cancel()

    def _load_economy_data(self):
        """Lädt die Economy-Daten aus der Datei."""
        try:
            with open("economy.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "users" in data:
                    # Neues Format mit Einstellungen
                    self.economy_data = data.get("users", {})
                    
                    # Lade Einstellungen, behalte aber Standardwerte wenn nicht vorhanden
                    if "settings" in data and "global" in data["settings"]:
                        # Füge neue Einstellungen hinzu und behalte bestehende
                        for key, value in data["settings"]["global"].items():
                            self.settings["global"][key] = value
                else:
                    # Altes Format ohne Einstellungen
                    self.economy_data = data
        except (FileNotFoundError, json.JSONDecodeError):
            self.economy_data = {}
            self._save_economy_data()
            logger.info("Neue Economy-Datei erstellt")

    def _save_economy_data(self):
        """Speichert die Economy-Daten in der Datei."""
        data = {
            "users": self.economy_data,
            "settings": self.settings
        }
        with open("economy.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def _get_user_data(self, user_id: str, guild_id: str) -> Dict:
        """Holt die Daten eines Benutzers oder erstellt einen neuen Eintrag."""
        if guild_id not in self.economy_data:
            self.economy_data[guild_id] = {}

        if user_id not in self.economy_data[guild_id]:
            self.economy_data[guild_id][user_id] = {
                "credits": 0,
                "last_daily": None,
                "daily_streak": 0,
                "last_work": None,
                "inventory": []
            }
            self._save_economy_data()

        return self.economy_data[guild_id][user_id]

    def _add_credits(self, user_id: str, guild_id: str, amount: int):
        """Fügt einem Benutzer Credits hinzu."""
        user_data = self._get_user_data(user_id, guild_id)
        user_data["credits"] += amount
        self._save_economy_data()
        return user_data["credits"]

    def _remove_credits(self, user_id: str, guild_id: str, amount: int) -> bool:
        """
        Entfernt Credits von einem Benutzer.
        
        Returns:
            bool: True, wenn erfolgreich, False, wenn nicht genug Credits vorhanden sind.
        """
        user_data = self._get_user_data(user_id, guild_id)
        if user_data["credits"] < amount:
            return False
        
        user_data["credits"] -= amount
        self._save_economy_data()
        return True

    def _can_claim_daily(self, user_id: str, guild_id: str) -> tuple:
        """
        Prüft, ob ein Benutzer seine tägliche Belohnung abholen kann.
        
        Returns:
            tuple: (kann_abholen, verbleibende_zeit_in_sekunden, streak_verloren)
        """
        user_data = self._get_user_data(user_id, guild_id)
        
        # Hole die konfigurierbare Cooldown-Zeit
        daily_cooldown = self.settings["global"]["daily_cooldown"]
        # Berechne die Zeit, nach der ein Streak verloren geht (2x Cooldown)
        streak_reset_time = daily_cooldown * 2
        
        if user_data["last_daily"] is None:
            return (True, 0, False)
        
        last_daily = datetime.datetime.fromisoformat(user_data["last_daily"])
        now = datetime.datetime.now()
        
        # Berechne die vergangene Zeit in Sekunden
        delta = now - last_daily
        seconds_passed = delta.total_seconds()
        
        if seconds_passed >= daily_cooldown:
            # Prüfe, ob die Streak verloren wurde (mehr als doppelte Cooldown-Zeit)
            streak_lost = seconds_passed >= streak_reset_time
            return (True, 0, streak_lost)
        else:
            # Berechne die verbleibende Zeit in Sekunden
            seconds_left = daily_cooldown - seconds_passed
            return (False, seconds_left, False)

    def _format_time(self, seconds: float) -> str:
        """Formatiert Sekunden in ein lesbares Format (HH:MM:SS)."""
        hours, remainder = divmod(int(seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    @tasks.loop(minutes=5)
    async def check_daily_reset(self):
        """Überprüft und aktualisiert tägliche Resets."""
        pass  # Diese Funktion könnte später erweitert werden

    @check_daily_reset.before_loop
    async def before_check_daily_reset(self):
        """Warte, bis der Bot bereit ist."""
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="balance", aliases=["bal"], description="Zeigt deinen Kontostand an.")
    async def balance(self, ctx: commands.Context, user: Optional[discord.Member] = None):
        """
        Zeigt den Kontostand eines Benutzers an.
        
        Args:
            user: Der Benutzer, dessen Kontostand angezeigt werden soll. Wenn nicht angegeben, wird der eigene Kontostand angezeigt.
        """
        target = user or ctx.author
        user_id = str(target.id)
        guild_id = str(ctx.guild.id)
        
        user_data = self._get_user_data(user_id, guild_id)
        
        embed = discord.Embed(
            title="💰 Kontostand",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name=f"{target.display_name}'s Konto",
            value=f"**{user_data['credits']} Credits**",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="daily", description="Hole deine tägliche Belohnung ab.")
    @commands.cooldown(1, 5, commands.BucketType.user)  # Verhindert Spam
    async def daily(self, ctx: commands.Context):
        """
        Gibt dem Benutzer eine tägliche Belohnung von Credits.
        Streaks geben Bonusbelohnungen.
        """
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        
        # Einstellungen abrufen
        daily_base = self.settings["global"]["daily_base"]
        daily_streak_bonus = self.settings["global"]["daily_streak_bonus"]
        daily_max_streak = self.settings["global"]["daily_max_streak"]
        daily_cooldown = self.settings["global"]["daily_cooldown"]
        
        can_claim, seconds_left, streak_lost = self._can_claim_daily(user_id, guild_id)
        
        if not can_claim:
            formatted_time = self._format_time(seconds_left)
            await ctx.send(f"❌ Du kannst deine tägliche Belohnung erst in **{formatted_time}** wieder abholen!")
            return
        
        user_data = self._get_user_data(user_id, guild_id)
        
        # Setze die Streak zurück, wenn sie verloren wurde
        if streak_lost:
            user_data["daily_streak"] = 0
        
        # Erhöhe die Streak und berechne die Belohnung
        user_data["daily_streak"] += 1
        streak = user_data["daily_streak"]
        
        # Basisbelohnung + Streakbonus
        base_reward = daily_base
        # Begrenze den Streak-Bonus auf die maximale Streak
        effective_streak = min(streak, daily_max_streak)
        streak_bonus = effective_streak * daily_streak_bonus
        
        reward = base_reward + streak_bonus
        
        # Aktualisiere die Daten
        user_data["last_daily"] = datetime.datetime.now().isoformat()
        user_data["credits"] += reward
        self._save_economy_data()
        
        # Erstelle ein Embed für die Antwort
        embed = discord.Embed(
            title="✅ Tägliche Belohnung",
            description=f"Du hast **{reward} Credits** erhalten!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Aufschlüsselung",
            value=f"Basis: **{base_reward} Credits**\nStreak Bonus ({streak} Tage): **{streak_bonus} Credits**",
            inline=False
        )
        
        embed.add_field(
            name="Neuer Kontostand",
            value=f"**{user_data['credits']} Credits**",
            inline=False
        )
        
        # Zeige an, ob der Spieler den maximalen Streak-Bonus erreicht hat
        if streak >= daily_max_streak:
            streak_info = f"Streak: {streak} Tage in Folge! Du erhältst den maximalen Streak-Bonus!"
        else:
            streak_info = f"Streak: {streak} Tage in Folge! Komm morgen wieder, um deine Streak zu verlängern."
        
        embed.set_footer(text=streak_info)
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="work", description="Arbeite, um Credits zu verdienen.")
    @commands.cooldown(1, 3600, commands.BucketType.user)  # Standardwert, wird durch Einstellungen überschrieben
    async def work(self, ctx: commands.Context):
        """
        Lässt den Benutzer arbeiten, um Credits zu verdienen.
        Hat einen konfigurierbaren Cooldown.
        """
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        
        # Einstellungen abrufen
        work_min = self.settings["global"]["work_min"]
        work_max = self.settings["global"]["work_max"]
        work_cooldown = self.settings["global"]["work_cooldown"]
        
        # Überprüfe, ob der Benutzer schon gearbeitet hat (zusätzlich zum Cooldown)
        user_data = self._get_user_data(user_id, guild_id)
        
        if user_data["last_work"] is not None:
            last_work = datetime.datetime.fromisoformat(user_data["last_work"])
            now = datetime.datetime.now()
            delta = now - last_work
            
            if delta.total_seconds() < work_cooldown:
                seconds_left = work_cooldown - delta.total_seconds()
                formatted_time = self._format_time(seconds_left)
                await ctx.send(f"❌ Du musst dich ausruhen! Du kannst in **{formatted_time}** wieder arbeiten.")
                return
        
        # Erstelle eine Liste von möglichen Jobs mit unterschiedlichen Faktoren für Belohnungen
        jobs = [
            {"name": "Kassierer", "min_factor": 0.5, "max_factor": 0.8},
            {"name": "Kellner", "min_factor": 0.6, "max_factor": 0.9},
            {"name": "Lieferfahrer", "min_factor": 0.7, "max_factor": 1.0},
            {"name": "IT-Support", "min_factor": 0.8, "max_factor": 1.2},
            {"name": "Grafikdesigner", "min_factor": 0.9, "max_factor": 1.3},
            {"name": "Programmierer", "min_factor": 1.0, "max_factor": 1.5},
            {"name": "Social Media Manager", "min_factor": 0.7, "max_factor": 1.1},
            {"name": "Journalist", "min_factor": 0.75, "max_factor": 1.15},
            {"name": "Lehrer", "min_factor": 0.85, "max_factor": 1.25},
        ]
        
        # Wähle einen zufälligen Job
        job = random.choice(jobs)
        
        # Berechne die tatsächlichen Min- und Max-Werte für den Job
        job_min = max(1, int(work_min * job["min_factor"]))
        job_max = max(job_min, int(work_max * job["max_factor"]))
        
        # Berechne die Belohnung
        earned = random.randint(job_min, job_max)
        
        # Aktualisiere die Daten des Benutzers
        user_data["last_work"] = datetime.datetime.now().isoformat()
        user_data["credits"] += earned
        self._save_economy_data()
        
        # Erstelle ein Embed für die Antwort
        embed = discord.Embed(
            title="💼 Arbeit",
            description=f"Du hast als **{job['name']}** gearbeitet und **{earned} Credits** verdient!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Neuer Kontostand",
            value=f"**{user_data['credits']} Credits**",
            inline=False
        )
        
        # Zeige Cooldown in formatierten Zeit an
        cooldown_str = self._format_time(work_cooldown)
        embed.set_footer(text=f"Du kannst in {cooldown_str} wieder arbeiten.")
        
        # Aktualisiere den Cooldown basierend auf den Einstellungen
        try:
            self.work.reset_cooldown(ctx)
            self.work._buckets = commands.CooldownMapping.from_cooldown(
                1, work_cooldown, commands.BucketType.user
            )
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Cooldowns: {e}")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="pay", description="Überweise Credits an einen anderen Benutzer.")
    async def pay(self, ctx: commands.Context, user: discord.Member, amount: int):
        """
        Überweist Credits an einen anderen Benutzer.
        Mit konfigurierbarer Steuer und Mindestbetrag.
        
        Args:
            user: Der Benutzer, der Credits erhalten soll.
            amount: Die Anzahl der zu überweisenden Credits.
        """
        # Hole die Einstellungen
        pay_tax = self.settings["global"]["pay_tax"]
        pay_min = self.settings["global"]["pay_min"]
        
        # Überprüfe, ob der Betrag den Mindestbetrag erreicht
        if amount < pay_min:
            await ctx.send(f"❌ Der Mindestbetrag für Überweisungen beträgt **{pay_min} Credits**!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Der Betrag muss positiv sein!")
            return
        
        sender_id = str(ctx.author.id)
        receiver_id = str(user.id)
        guild_id = str(ctx.guild.id)
        
        # Überprüfe, ob der Sender sich nicht selbst Geld sendet
        if sender_id == receiver_id:
            await ctx.send("❌ Du kannst dir nicht selbst Credits überweisen!")
            return
        
        # Berechne den Steuerbetrag
        tax_amount = int(amount * pay_tax)
        actual_amount = amount - tax_amount
        
        # Überprüfe, ob der Sender genug Credits hat
        sender_data = self._get_user_data(sender_id, guild_id)
        
        if sender_data["credits"] < amount:
            await ctx.send(f"❌ Du hast nicht genug Credits! Du benötigst {amount} Credits, hast aber nur {sender_data['credits']}.")
            return
        
        # Führe die Überweisung durch
        sender_data["credits"] -= amount
        
        receiver_data = self._get_user_data(receiver_id, guild_id)
        receiver_data["credits"] += actual_amount
        
        self._save_economy_data()
        
        # Erstelle ein Embed für die Antwort
        embed = discord.Embed(
            title="💸 Überweisung",
            description=f"Du hast **{amount} Credits** überwiesen!",
            color=discord.Color.green()
        )
        
        # Füge Steuerinformationen hinzu, wenn eine Steuer erhoben wurde
        if tax_amount > 0:
            embed.add_field(
                name="Steuer",
                value=f"**{tax_amount} Credits** ({int(pay_tax*100)}%) wurden als Steuer einbehalten.",
                inline=False
            )
            embed.add_field(
                name="Erhaltener Betrag",
                value=f"{user.mention} hat **{actual_amount} Credits** erhalten.",
                inline=False
            )
        else:
            embed.add_field(
                name="Erhaltener Betrag",
                value=f"{user.mention} hat **{actual_amount} Credits** erhalten.",
                inline=False
            )
        
        embed.add_field(
            name="Dein neuer Kontostand",
            value=f"**{sender_data['credits']} Credits**",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="richlist", aliases=["top", "toplist"], description="Zeigt die Rangliste der reichsten Benutzer an.")
    async def richlist(self, ctx: commands.Context):
        """
        Zeigt eine Rangliste der reichsten Benutzer auf dem Server an.
        """
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.economy_data or not self.economy_data[guild_id]:
            await ctx.send("❌ Es gibt noch keine Wirtschaftsdaten für diesen Server!")
            return
        
        # Sortiere die Benutzer nach Credits
        sorted_users = sorted(
            self.economy_data[guild_id].items(),
            key=lambda x: x[1]['credits'],
            reverse=True
        )
        
        # Begrenze auf die Top 10
        top_users = sorted_users[:10]
        
        embed = discord.Embed(
            title="💰 Rangliste - Die Reichsten Benutzer",
            color=discord.Color.gold()
        )
        
        for i, (user_id, data) in enumerate(top_users, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                username = user.display_name
            except:
                username = f"Unbekannter Benutzer ({user_id})"
            
            embed.add_field(
                name=f"{i}. {username}",
                value=f"**{data['credits']} Credits**",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="rob", description="Versuche, einen anderen Benutzer auszurauben.")
    @commands.cooldown(1, 7200, commands.BucketType.user)  # Standardwert, wird durch Einstellungen überschrieben
    async def rob(self, ctx: commands.Context, user: discord.Member):
        """
        Versucht, einen anderen Benutzer auszurauben.
        Hat eine Chance zu scheitern und eine Strafe zu bekommen.
        Wahrscheinlichkeit, Belohnungen und Strafen sind konfigurierbar.
        
        Args:
            user: Der Benutzer, der ausgeraubt werden soll.
        """
        if user.id == ctx.author.id:
            await ctx.send("❌ Du kannst dich nicht selbst ausrauben!")
            return
        
        if user.bot:
            await ctx.send("❌ Du kannst keine Bots ausrauben!")
            return
        
        # Lade die Einstellungen
        rob_chance = self.settings["global"]["rob_chance"]
        rob_min_percent = self.settings["global"]["rob_min_percent"]
        rob_max_percent = self.settings["global"]["rob_max_percent"]
        rob_cooldown = self.settings["global"]["rob_cooldown"]
        rob_fail_min = self.settings["global"]["rob_fail_min"]
        rob_fail_max = self.settings["global"]["rob_fail_max"]
        
        robber_id = str(ctx.author.id)
        victim_id = str(user.id)
        guild_id = str(ctx.guild.id)
        
        # Lade die Daten
        robber_data = self._get_user_data(robber_id, guild_id)
        victim_data = self._get_user_data(victim_id, guild_id)
        
        # Prüfe, ob das Opfer genug Credits hat (mindestens das Doppelte der minimalen Strafe)
        min_credits = rob_fail_min * 2
        if victim_data["credits"] < min_credits:
            await ctx.send(f"❌ {user.display_name} hat nicht genug Credits, um ausgeraubt zu werden!")
            ctx.command.reset_cooldown(ctx)  # Setze den Cooldown zurück
            return
        
        # Prüfe, ob der Räuber genug Credits hat (für potenzielle Strafen)
        if robber_data["credits"] < rob_fail_min:
            await ctx.send(f"❌ Du hast nicht genug Credits, um einen Raubversuch zu wagen! Du brauchst mindestens {rob_fail_min} Credits.")
            ctx.command.reset_cooldown(ctx)
            return
        
        # Berechne die Erfolgswahrscheinlichkeit
        success = random.random() < rob_chance
        
        if success:
            # Erfolgreicher Raub: Stehle einen Prozentsatz der Credits des Opfers
            steal_percent = random.uniform(rob_min_percent, rob_max_percent)
            stolen_amount = int(victim_data["credits"] * steal_percent)
            
            # Begrenze den gestohlenen Betrag auf maximal den konfigurierten Prozentsatz
            stolen_amount = min(stolen_amount, int(victim_data["credits"] * rob_max_percent))
            
            # Übertrage die Credits
            victim_data["credits"] -= stolen_amount
            robber_data["credits"] += stolen_amount
            
            embed = discord.Embed(
                title="🔫 Erfolgreicher Raub!",
                description=f"Du hast **{stolen_amount} Credits** von {user.mention} gestohlen!",
                color=discord.Color.green()
            )
            
            embed.add_field(
                name="Dein neuer Kontostand",
                value=f"**{robber_data['credits']} Credits**",
                inline=False
            )
            
            # Zeige Cooldown in der Nachricht an
            cooldown_str = self._format_time(rob_cooldown)
            embed.set_footer(text=f"Cooldown: {cooldown_str}")
            
            # Speichere die Daten
            self._save_economy_data()
            
        else:
            # Gescheiterter Raub: Verliere eine konfigurierbare Anzahl Credits als Strafe
            if rob_fail_min >= rob_fail_max:
                penalty = rob_fail_min
            else:
                penalty = random.randint(rob_fail_min, rob_fail_max)
            
            # Begrenze die Strafe auf die verfügbaren Credits
            penalty = min(penalty, robber_data["credits"])
            
            robber_data["credits"] -= penalty
            
            embed = discord.Embed(
                title="❌ Gescheiterter Raub!",
                description=f"Du wurdest erwischt und musst **{penalty} Credits** Strafe zahlen!",
                color=discord.Color.red()
            )
            
            embed.add_field(
                name="Dein neuer Kontostand",
                value=f"**{robber_data['credits']} Credits**",
                inline=False
            )
            
            # Zeige Cooldown in der Nachricht an
            cooldown_str = self._format_time(rob_cooldown)
            embed.set_footer(text=f"Cooldown: {cooldown_str}")
            
            # Speichere die Daten
            self._save_economy_data()
        
        # Aktualisiere den Cooldown basierend auf den Einstellungen
        try:
            self.rob.reset_cooldown(ctx)
            self.rob._buckets = commands.CooldownMapping.from_cooldown(
                1, rob_cooldown, commands.BucketType.user
            )
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Cooldowns: {e}")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="beg", description="Bettle um ein paar Credits.")
    @commands.cooldown(1, 300, commands.BucketType.user)  # Standardwert, wird durch Einstellungen überschrieben
    async def beg(self, ctx: commands.Context):
        """
        Bettle um ein paar Credits.
        Du hast eine Chance, eine kleine Menge an Credits zu bekommen oder leer auszugehen.
        Wahrscheinlichkeit, Belohnungen und Verluste sind konfigurierbar.
        """
        user_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id)
        user_data = self._get_user_data(user_id, guild_id)
        
        # Hole die Einstellungen
        beg_chance = self.settings["global"]["beg_chance"]
        beg_min = self.settings["global"]["beg_min"]
        beg_max = self.settings["global"]["beg_max"]
        beg_cooldown = self.settings["global"]["beg_cooldown"]
        beg_fail_loss = self.settings["global"]["beg_fail_loss"]
        
        # Zufällige Personen, die dem Bettler helfen könnten
        helpers = [
            "ein freundlicher Passant", 
            "eine alte Dame", 
            "der Serverbesitzer", 
            "ein Millionär", 
            "ein mitfühlender Fremder",
            "ein großzügiger Tourist",
            "ein bekannter Streamer",
            "ein Mitglied der königlichen Familie"
        ]
        
        # Ablehnungsnachrichten
        rejection_messages = [
            "hat dich komplett ignoriert",
            "hat so getan, als würde er dich nicht sehen",
            "hat dir einen leeren Geldbeutel gezeigt",
            "hat dir gesagt, du sollst arbeiten gehen",
            "hat dir einen mitleidigen Blick zugeworfen, aber nichts gegeben",
            "ist schnell in die andere Richtung gelaufen"
        ]
        
        if random.random() < beg_chance:
            # Erfolgreich gebettelt
            amount = random.randint(beg_min, beg_max)
            helper = random.choice(helpers)
            
            self._add_credits(user_id, guild_id, amount)
            user_data = self._get_user_data(user_id, guild_id)  # Aktualisierte Daten holen
            
            embed = discord.Embed(
                title="🙏 Erfolgreiches Betteln",
                description=f"{helper} hat dir **{amount} Credits** gegeben!",
                color=discord.Color.green()
            )
            
            # Zeige Cooldown in der Nachricht an
            cooldown_str = self._format_time(beg_cooldown)
            embed.set_footer(text=f"Neuer Kontostand: {user_data['credits']} Credits | Cooldown: {cooldown_str}")
            
        else:
            # Nicht erfolgreich
            helper = random.choice(helpers)
            rejection = random.choice(rejection_messages)
            
            # Bei negativem Wert für beg_fail_loss erleidet der Spieler einen Verlust
            loss_text = ""
            if beg_fail_loss > 0 and user_data["credits"] > 0:
                # Verlust kann nicht mehr sein als was der Spieler hat
                actual_loss = min(beg_fail_loss, user_data["credits"])
                self._remove_credits(user_id, guild_id, actual_loss)
                user_data = self._get_user_data(user_id, guild_id)  # Aktualisierte Daten holen
                loss_text = f"\n\nDu hast dabei **{actual_loss} Credits** verloren!"
            
            embed = discord.Embed(
                title="🙁 Betteln fehlgeschlagen",
                description=f"{helper} {rejection}.{loss_text}",
                color=discord.Color.red()
            )
            
            # Zeige Cooldown in der Nachricht an
            cooldown_str = self._format_time(beg_cooldown)
            embed.set_footer(text=f"Kontostand: {user_data['credits']} Credits | Cooldown: {cooldown_str}")
        
        # Aktualisiere den Cooldown basierend auf den Einstellungen
        try:
            self.beg.reset_cooldown(ctx)
            self.beg._buckets = commands.CooldownMapping.from_cooldown(
                1, beg_cooldown, commands.BucketType.user
            )
        except Exception as e:
            logger.error(f"Fehler beim Aktualisieren des Cooldowns: {e}")
        
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="economy_help", description="Zeigt Hilfe zu allen Economy-Befehlen an.")
    async def economy_help(self, ctx: commands.Context):
        """
        Zeigt eine Hilfeseite mit allen verfügbaren Economy-Befehlen an.
        """
        embed = discord.Embed(
            title="💰 Economy-Befehle Hilfe",
            description="Hier sind alle verfügbaren Economy-Befehle und ihre Funktionen:",
            color=discord.Color.gold()
        )
        
        commands_info = [
            {
                "name": "balance",
                "value": "Zeigt deinen Kontostand oder den eines anderen Nutzers an.\n`/balance [user]`",
                "inline": False
            },
            {
                "name": "daily",
                "value": f"Hole deine tägliche Belohnung ab. Längere Streaks geben mehr Credits!\nCooldown: {self._format_time(self.settings['global']['daily_cooldown'])}\n`/daily`",
                "inline": False
            },
            {
                "name": "work",
                "value": f"Arbeite, um Credits zu verdienen. Verschiedene Jobs geben unterschiedliche Belohnungen.\nCooldown: {self._format_time(self.settings['global']['work_cooldown'])}\n`/work`",
                "inline": False
            },
            {
                "name": "beg",
                "value": f"Bettle um ein paar Credits. {int(self.settings['global']['beg_chance']*100)}% Erfolgswahrscheinlichkeit.\nBelohnung: {self.settings['global']['beg_min']}-{self.settings['global']['beg_max']} Credits\nCooldown: {self._format_time(self.settings['global']['beg_cooldown'])}\n`/beg`",
                "inline": False
            },
            {
                "name": "pay",
                "value": "Überweise Credits an einen anderen Nutzer.\n`/pay <user> <amount>`",
                "inline": False
            },
            {
                "name": "rob",
                "value": f"Versuche einen anderen Nutzer auszurauben. {int(self.settings['global']['rob_chance']*100)}% Erfolgswahrscheinlichkeit.\nCooldown: {self._format_time(self.settings['global']['rob_cooldown'])}\n`/rob <user>`",
                "inline": False
            },
            {
                "name": "richlist",
                "value": "Zeigt eine Rangliste der reichsten Nutzer auf dem Server an.\n`/richlist`",
                "inline": False
            }
        ]
        
        # Admin-Befehle hervorheben, wenn der Benutzer Admin-Rechte hat
        if ctx.author.guild_permissions.administrator:
            commands_info.append({
                "name": "economy_settings",
                "value": "**[Admin]** Verwaltet die Einstellungen des Economy-Systems.\n`/economy_settings [setting] [value]`",
                "inline": False
            })
        
        for cmd in commands_info:
            embed.add_field(name=cmd["name"], value=cmd["value"], inline=cmd["inline"])
        
        embed.set_footer(text="Verwende einen dieser Befehle mit / oder dem eingestellten Präfix.")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="economy_settings", description="Verwaltet die Einstellungen des Economy-Systems.")
    @commands.has_permissions(administrator=True)
    async def economy_settings(self, ctx: commands.Context, setting: str = None, value: float = None):
        """
        Verwaltet die Einstellungen des Economy-Systems.
        Nur für Administratoren.
        
        Args:
            setting: Die Einstellung, die geändert werden soll (z.B. beg_chance, beg_min, beg_max, rob_chance, etc.)
            value: Der neue Wert für die Einstellung
        """
        if setting is None:
            # Zeige alle Einstellungen kategorisiert an
            settings = self.settings["global"]
            embed = discord.Embed(
                title="⚙️ Economy-Einstellungen",
                description="Hier sind die aktuellen Einstellungen für das Economy-System.\nKlicke auf die Kategorien unten, um zu den spezifischen Einstellungen zu navigieren.",
                color=discord.Color.blue()
            )
            
            # Gruppiere Einstellungen nach Befehlen
            beg_settings = {k: v for k, v in settings.items() if k.startswith("beg_")}
            work_settings = {k: v for k, v in settings.items() if k.startswith("work_")}
            daily_settings = {k: v for k, v in settings.items() if k.startswith("daily_")}
            rob_settings = {k: v for k, v in settings.items() if k.startswith("rob_")}
            pay_settings = {k: v for k, v in settings.items() if k.startswith("pay_")}
            
            # Erstelle eine Zusammenfassung der Befehle mit exakten Einstellungsbefehlen
            embed.add_field(
                name="🙏 Beg-Befehl",
                value=f"Chance: **{int(beg_settings['beg_chance']*100)}%** `/economy_settings beg_chance 0.7`\n"
                      f"Belohnung: **{beg_settings['beg_min']}-{beg_settings['beg_max']} Credits** `/economy_settings beg_min 5` `/economy_settings beg_max 25`\n"
                      f"Cooldown: **{self._format_time(beg_settings['beg_cooldown'])}** `/economy_settings beg_cooldown 300`\n"
                      f"Verluststafe: **{beg_settings['beg_fail_loss']} Credits** `/economy_settings beg_fail_loss 0`",
                inline=False
            )
            
            embed.add_field(
                name="💼 Work-Befehl",
                value=f"Belohnungsbereich: **{work_settings['work_min']}-{work_settings['work_max']} Credits**\n"
                      f"→ Min: `/economy_settings work_min {work_settings['work_min']}`\n"
                      f"→ Max: `/economy_settings work_max {work_settings['work_max']}`\n"
                      f"Cooldown: **{self._format_time(work_settings['work_cooldown'])}**\n"
                      f"→ Ändern: `/economy_settings work_cooldown {work_settings['work_cooldown']}`",
                inline=False
            )
            
            embed.add_field(
                name="📅 Daily-Befehl",
                value=f"Grundbelohnung: **{daily_settings['daily_base']} Credits** `/economy_settings daily_base {daily_settings['daily_base']}`\n"
                      f"Streak-Bonus: **{daily_settings['daily_streak_bonus']} Credits pro Tag** `/economy_settings daily_streak_bonus {daily_settings['daily_streak_bonus']}`\n"
                      f"Max. Streak: **{daily_settings['daily_max_streak']} Tage** `/economy_settings daily_max_streak {daily_settings['daily_max_streak']}`\n"
                      f"Cooldown: **{self._format_time(daily_settings['daily_cooldown'])}** `/economy_settings daily_cooldown {daily_settings['daily_cooldown']}`",
                inline=False
            )
            
            embed.add_field(
                name="🔫 Rob-Befehl",
                value=f"Chance: **{int(rob_settings['rob_chance']*100)}%** `/economy_settings rob_chance {rob_settings['rob_chance']}`\n"
                      f"Diebesgut: **{int(rob_settings['rob_min_percent']*100)}-{int(rob_settings['rob_max_percent']*100)}%** vom Opfer\n"
                      f"→ Min %: `/economy_settings rob_min_percent {rob_settings['rob_min_percent']}`\n"
                      f"→ Max %: `/economy_settings rob_max_percent {rob_settings['rob_max_percent']}`\n"
                      f"Strafe: **{rob_settings['rob_fail_min']}-{rob_settings['rob_fail_max']} Credits**\n"
                      f"→ Min: `/economy_settings rob_fail_min {rob_settings['rob_fail_min']}`\n"
                      f"→ Max: `/economy_settings rob_fail_max {rob_settings['rob_fail_max']}`\n"
                      f"Cooldown: **{self._format_time(rob_settings['rob_cooldown'])}** `/economy_settings rob_cooldown {rob_settings['rob_cooldown']}`",
                inline=False
            )
            
            embed.add_field(
                name="💸 Pay-Befehl",
                value=f"Steuer: **{int(pay_settings['pay_tax']*100)}%** `/economy_settings pay_tax {pay_settings['pay_tax']}`\n"
                      f"Min. Betrag: **{pay_settings['pay_min']} Credits** `/economy_settings pay_min {pay_settings['pay_min']}`",
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Hinweis zur Benutzung",
                value="Verwende `/economy_settings [einstellung] [wert]`, um Werte zu ändern.\n"
                      "Beispiel: `/economy_settings beg_chance 0.8` für 80% Bettelerfolg.\n\n"
                      "Für eine Liste aller Einstellungen, verwende `/economy_settings list`.",
                inline=False
            )
            
            await ctx.send(embed=embed)
            return
        
        # Zeige die Liste aller verfügbaren Einstellungen
        if setting.lower() == "list":
            settings = self.settings["global"]
            embed = discord.Embed(
                title="📋 Liste aller Economy-Einstellungen",
                description="Hier sind alle verfügbaren Einstellungen nach Kategorie sortiert:",
                color=discord.Color.gold()
            )
            
            # Erstelle Listen für die verschiedenen Befehlskategorien mit den Befehlen
            beg_list = "\n".join([f"`{k}`: {self._format_setting_value(k, v)} → `/economy_settings {k} [wert]`" for k, v in settings.items() if k.startswith("beg_")])
            work_list = "\n".join([f"`{k}`: {self._format_setting_value(k, v)} → `/economy_settings {k} [wert]`" for k, v in settings.items() if k.startswith("work_")])
            daily_list = "\n".join([f"`{k}`: {self._format_setting_value(k, v)} → `/economy_settings {k} [wert]`" for k, v in settings.items() if k.startswith("daily_")])
            rob_list = "\n".join([f"`{k}`: {self._format_setting_value(k, v)} → `/economy_settings {k} [wert]`" for k, v in settings.items() if k.startswith("rob_")])
            pay_list = "\n".join([f"`{k}`: {self._format_setting_value(k, v)} → `/economy_settings {k} [wert]`" for k, v in settings.items() if k.startswith("pay_")])
            
            embed.add_field(name="🙏 Beg-Befehl Einstellungen", value=beg_list, inline=False)
            embed.add_field(name="💼 Work-Befehl Einstellungen", value=work_list, inline=False)
            embed.add_field(name="📅 Daily-Befehl Einstellungen", value=daily_list, inline=False)
            embed.add_field(name="🔫 Rob-Befehl Einstellungen", value=rob_list, inline=False)
            embed.add_field(name="💸 Pay-Befehl Einstellungen", value=pay_list, inline=False)
            
            await ctx.send(embed=embed)
            return
        
        # Überprüfe, ob die Einstellung existiert
        if setting not in self.settings["global"]:
            await ctx.send(f"❌ Die Einstellung `{setting}` existiert nicht.\nVerwende `/economy_settings list` für alle verfügbaren Einstellungen.")
            return
        
        if value is None:
            # Zeige nur die angegebene Einstellung
            current_value = self.settings["global"][setting]
            formatted_value = self._format_setting_value(setting, current_value)
            
            # Beziehe Beschreibung/Hilfetext für diese Einstellung
            description = self._get_setting_description(setting)
            
            embed = discord.Embed(
                title=f"🔍 Einstellung: {setting}",
                description=description,
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="Aktueller Wert", 
                value=formatted_value,
                inline=False
            )
            
            embed.set_footer(text=f"Befehl zum Ändern: /economy_settings {setting} <wert>")
            
            await ctx.send(embed=embed)
            return
        
        # Validiere und setze den neuen Wert
        old_value = self.settings["global"][setting]
        
        # Spezielle Validierung für bestimmte Einstellungen
        if "chance" in setting:
            if value < 0 or value > 1:
                await ctx.send("❌ Chancenwerte müssen zwischen 0 und 1 liegen (z.B. 0.5 für 50%).")
                return
        elif "cooldown" in setting:
            if value < 0:
                await ctx.send("❌ Cooldowns können nicht negativ sein.")
                return
        elif setting.endswith("_tax"):
            if value < 0 or value > 1:
                await ctx.send("❌ Steuerwerte müssen zwischen 0 und 1 liegen (z.B. 0.05 für 5%).")
                return
        elif "percent" in setting:
            if value < 0 or value > 1:
                await ctx.send("❌ Prozentwerte müssen zwischen 0 und 1 liegen (z.B. 0.3 für 30%).")
                return
        elif "min" in setting or "max" in setting or "base" in setting or "bonus" in setting:
            if value < 0:
                await ctx.send("❌ Beträge und Bonuswerte können nicht negativ sein.")
                return
        
        # Spezielle Paar-Validierung für min-max-Paare
        if setting.endswith("_min"):
            max_setting = setting.replace("_min", "_max")
            if max_setting in self.settings["global"] and value > self.settings["global"][max_setting]:
                await ctx.send(f"❌ Der Minimalwert kann nicht größer sein als der Maximalwert ({self.settings['global'][max_setting]}).")
                return
        elif setting.endswith("_max"):
            min_setting = setting.replace("_max", "_min")
            if min_setting in self.settings["global"] and value < self.settings["global"][min_setting]:
                await ctx.send(f"❌ Der Maximalwert kann nicht kleiner sein als der Minimalwert ({self.settings['global'][min_setting]}).")
                return
        
        # Aktualisiere die Einstellung
        self.settings["global"][setting] = value
        self._save_economy_data()
        
        # Formatiere die alten und neuen Werte für die Anzeige
        old_formatted = self._format_setting_value(setting, old_value)
        new_formatted = self._format_setting_value(setting, value)
        
        await ctx.send(f"✅ Die Einstellung `{setting}` wurde erfolgreich geändert.\n**Alter Wert:** {old_formatted}\n**Neuer Wert:** {new_formatted}")
        
        # Wenn ein Cooldown geändert wurde, aktualisiere die Befehle
        if setting == "beg_cooldown":
            self.beg.reset_cooldown(ctx)
            self.beg._buckets = commands.CooldownMapping.from_cooldown(1, value, commands.BucketType.user)
        elif setting == "work_cooldown":
            self.work.reset_cooldown(ctx)
            self.work._buckets = commands.CooldownMapping.from_cooldown(1, value, commands.BucketType.user)
        elif setting == "rob_cooldown":
            self.rob.reset_cooldown(ctx)
            self.rob._buckets = commands.CooldownMapping.from_cooldown(1, value, commands.BucketType.user)
            
    def _format_setting_value(self, setting: str, value: float) -> str:
        """Formatiert den Wert einer Einstellung für die Anzeige."""
        if "cooldown" in setting:
            return self._format_time(value)
        elif "chance" in setting or "percent" in setting or setting.endswith("_tax"):
            return f"{int(value * 100)}%"
        else:
            return str(value)
            
    def _get_setting_description(self, setting: str) -> str:
        """Gibt eine Beschreibung für eine bestimmte Einstellung zurück."""
        descriptions = {
            # Beg-Befehl Einstellungen
            "beg_chance": "Die Wahrscheinlichkeit, dass ein Betteln erfolgreich ist (0-1).",
            "beg_min": "Die minimale Anzahl an Credits, die man beim Betteln erhalten kann.",
            "beg_max": "Die maximale Anzahl an Credits, die man beim Betteln erhalten kann.",
            "beg_cooldown": "Die Abklingzeit zwischen zwei Bettelversuchen in Sekunden.",
            "beg_fail_loss": "Die Anzahl an Credits, die man verliert, wenn das Betteln fehlschlägt (0 für keinen Verlust).",
            
            # Work-Befehl Einstellungen
            "work_min": "Die minimale Basis für Arbeitsbelohnungen. Der tatsächliche Wert kann je nach Job variieren.",
            "work_max": "Die maximale Basis für Arbeitsbelohnungen. Der tatsächliche Wert kann je nach Job variieren.",
            "work_cooldown": "Die Abklingzeit zwischen zwei Arbeitsschichten in Sekunden.",
            
            # Daily-Befehl Einstellungen
            "daily_base": "Die Basisbelohnung für den täglichen Befehl (ohne Streak-Bonus).",
            "daily_streak_bonus": "Die zusätzlichen Credits pro Tag Streak.",
            "daily_max_streak": "Die maximale Anzahl von Tagen, die für den Streak-Bonus berücksichtigt werden.",
            "daily_cooldown": "Die Abklingzeit zwischen zwei täglichen Belohnungen in Sekunden.",
            
            # Rob-Befehl Einstellungen
            "rob_chance": "Die Wahrscheinlichkeit, dass ein Raubversuch erfolgreich ist (0-1).",
            "rob_min_percent": "Der minimale Prozentsatz des Guthabens des Opfers, den man stehlen kann (0-1).",
            "rob_max_percent": "Der maximale Prozentsatz des Guthabens des Opfers, den man stehlen kann (0-1).",
            "rob_cooldown": "Die Abklingzeit zwischen zwei Raubversuchen in Sekunden.",
            "rob_fail_min": "Die minimale Strafe in Credits bei einem fehlgeschlagenen Raubversuch.",
            "rob_fail_max": "Die maximale Strafe in Credits bei einem fehlgeschlagenen Raubversuch.",
            
            # Pay-Befehl Einstellungen
            "pay_tax": "Die Steuer auf Überweisungen (0-1). Ein Wert von 0.05 bedeutet, dass 5% der überwiesenen Credits als Steuer abgezogen werden.",
            "pay_min": "Der Mindestbetrag, der überwiesen werden kann."
        }
        
        return descriptions.get(setting, "Keine Beschreibung verfügbar.")

async def setup(bot: commands.Bot):
    """Fügt den Economy-Cog zum Bot hinzu."""
    await bot.add_cog(Economy(bot))
    logger.info("Economy cog loaded")