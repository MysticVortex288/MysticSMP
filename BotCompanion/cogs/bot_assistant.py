import discord
from discord.ext import commands
from discord import app_commands
import logging
import json
import os
import difflib
import random
from typing import List, Dict, Optional

logger = logging.getLogger('discord_bot')

class BotAssistant(commands.Cog):
    """
    Ein Assistent, der Fragen über den Bot beantworten kann.
    Benutzer können Fragen stellen, und der Bot gibt hilfreiche Antworten.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config_file = "bot_assistant.json"
        self.faqs = self._load_faqs()
        # Standardwerte für Konfiguration setzen, falls sie nicht existieren
        if "assistant_channels" not in self.faqs:
            self.faqs["assistant_channels"] = {}
            self._save_faqs(self.faqs)
        logger.info("BotAssistant cog initialized")
    
    def _load_faqs(self) -> Dict:
        """Lade die FAQs aus der Datei oder erstelle eine Standard-FAQ-Liste."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Erstelle Standard-FAQs
            default_faqs = {
                "faqs": [
                    {
                        "question": "Was kann dieser Bot alles?",
                        "answer": "Dieser Bot bietet viele Funktionen wie Invite-Tracking, Level-System, Ticket-System, Counting-Game, temporäre Sprachkanäle, Verifizierung, Content-Ankündigungen und Self-Roles.",
                        "aliases": ["Was macht der Bot?", "Was sind die Funktionen des Bots?", "Funktionen", "Features"],
                        "category": "Allgemein"
                    },
                    {
                        "question": "Wie kann ich den Bot einrichten?",
                        "answer": "Die meisten Funktionen haben eigene Setup-Befehle. Beispiele: `/setuplevel` für das Level-System, `/setupticket` für das Ticket-System, `/setupvoice` für temporäre Sprachkanäle, usw.",
                        "aliases": ["Einrichtung", "Setup", "Wie starte ich?"],
                        "category": "Allgemein"
                    },
                    {
                        "question": "Welche Berechtigungen braucht der Bot?",
                        "answer": "Der Bot benötigt Administrator-Berechtigungen für die volle Funktionalität. Einige Funktionen funktionieren auch mit eingeschränkten Berechtigungen, aber für die beste Erfahrung empfehlen wir Administrator-Rechte.",
                        "aliases": ["Permissions", "Rechte", "Berechtigungen"],
                        "category": "Allgemein"
                    },
                    {
                        "question": "Wie funktioniert das Level-System?",
                        "answer": "Benutzer erhalten XP für Nachrichten (alle 60 Sekunden). Die XP führen zu Levels, und für bestimmte Levels können Rollen vergeben werden. Befehle: `/setuplevel`, `/rank`, `/leaderboard`.",
                        "aliases": ["XP", "Level", "Leveling", "Wie bekomme ich XP?"],
                        "category": "Level-System"
                    },
                    {
                        "question": "Wie funktioniert das Ticket-System?",
                        "answer": "Mit `/setupticket` richtest du das Ticket-System ein. Mit `/ticketpanel` erstellst du ein Panel, über das Benutzer Tickets erstellen können. Support-Rollen haben Zugriff auf Tickets und können sie schließen.",
                        "aliases": ["Tickets", "Support-Tickets", "Wie erstelle ich ein Ticket?"],
                        "category": "Ticket-System"
                    },
                    {
                        "question": "Wie funktionieren Self-Roles?",
                        "answer": "Mit `/createroles` kannst du ein Self-Roles Panel erstellen. Benutzer können Rollen durch Klicken auf die Buttons erhalten. Mit `/editroles` kannst du bestehende Panels bearbeiten. Rollen können in Kategorien organisiert werden.",
                        "aliases": ["Rollen", "Self-Rollen", "Wie bekomme ich Rollen?"],
                        "category": "Self-Roles"
                    },
                    {
                        "question": "Wie funktionieren temporäre Sprachkanäle?",
                        "answer": "Mit `/setupvoice` richtest du temporäre Sprachkanäle ein. Wenn Benutzer dem 'Erstelle einen Sprachkanal' beitreten, wird ein eigener Kanal erstellt, den sie kontrollieren können. Der Kanal wird gelöscht, wenn er leer ist.",
                        "aliases": ["Voice", "Sprachkanäle", "Temp-VC", "Wie erstelle ich einen Sprachkanal?"],
                        "category": "Temp-Voice"
                    },
                    {
                        "question": "Wie funktioniert das Counting-Game?",
                        "answer": "Mit `/countingsetup` richtest du das Counting-Game in einem Kanal ein. Benutzer müssen der Reihe nach zählen. Regeln: 1) Beginne mit 1, 2) Die nächste Zahl muss die vorherige + 1 sein, 3) Ein Benutzer darf nicht zweimal hintereinander zählen.",
                        "aliases": ["Counting", "Zählen", "Wie spiele ich das Zählspiel?"],
                        "category": "Counting-Game"
                    },
                    {
                        "question": "Wie funktioniert die Verifizierung?",
                        "answer": "Mit `/setupverify` richtest du das Verifizierungssystem ein. Es wird eine Nachricht mit einem Button gesendet. Wenn Benutzer auf den Button klicken, erhalten sie die Member-Rolle.",
                        "aliases": ["Verify", "Verifizierung", "Wie verifiziere ich mich?"],
                        "category": "Verifizierung"
                    },
                    {
                        "question": "Wie funktionieren Content-Ankündigungen?",
                        "answer": "Der Bot erkennt automatisch YouTube/Twitch/TikTok-Links und sendet eine Ankündigung. Mit `/setannouncementchannel` legst du den Kanal fest. Mit `/addtiktokcreator` kannst du TikTok-Creator tracken.",
                        "aliases": ["Content", "Ankündigungen", "YouTube", "Twitch", "TikTok"],
                        "category": "Content-Announcer"
                    },
                    {
                        "question": "Wie funktioniert das Invite-Tracking?",
                        "answer": "Der Bot verfolgt, wer wen eingeladen hat. Mit `/invites` siehst du die Einladungen eines Benutzers. Mit `/invite-leaderboard` wird eine Rangliste angezeigt. Diese Infos werden auch in Willkommensnachrichten verwendet.",
                        "aliases": ["Invites", "Einladungen", "Wer hat wen eingeladen?"],
                        "category": "Invite-Tracking"
                    },
                    {
                        "question": "Wie passe ich Willkommensnachrichten an?",
                        "answer": "Mit `/welcome channel` legst du den Kanal fest. Mit `/welcome message` kannst du die Nachricht anpassen. `/welcome variables` zeigt verfügbare Variablen an. `/welcome toggle` aktiviert/deaktiviert die Nachrichten.",
                        "aliases": ["Welcome", "Willkommen", "Begrüßung", "Wie begrüße ich neue Mitglieder?"],
                        "category": "Willkommensnachrichten"
                    },
                    {
                        "question": "Wie bekomme ich Hilfe bei einer bestimmten Funktion?",
                        "answer": "Du kannst `/help` verwenden, um allgemeine Hilfe zu erhalten. Mit `/help [Kategorie]` bekommst du spezifische Hilfe zu Funktionen wie 'level', 'ticket', 'roles', usw.",
                        "aliases": ["Hilfe", "Befehle", "Wie benutze ich eine Funktion?"],
                        "category": "Allgemein"
                    }
                ]
            }
            self._save_faqs(default_faqs)
            return default_faqs
    
    def _save_faqs(self, faqs: Dict) -> None:
        """Speichere die FAQs in der Datei."""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(faqs, f, indent=4, ensure_ascii=False)
    
    def _find_similar_question(self, query: str) -> Optional[Dict]:
        """Findet die ähnlichste Frage in der FAQ-Liste."""
        if not query or len(query) < 3:
            return None
        
        # Alle Fragen und ihre Aliase sammeln
        all_questions = []
        for faq in self.faqs["faqs"]:
            all_questions.append((faq["question"], faq))
            for alias in faq.get("aliases", []):
                all_questions.append((alias, faq))
        
        # Wenn es eine exakte Übereinstimmung gibt, diese zurückgeben
        for question, faq in all_questions:
            if query.lower() == question.lower():
                return faq
        
        # Ähnlichkeit zu allen Fragen berechnen
        similarities = []
        for question, faq in all_questions:
            similarity = difflib.SequenceMatcher(None, query.lower(), question.lower()).ratio()
            similarities.append((similarity, faq))
        
        # Nach Ähnlichkeit sortieren
        similarities.sort(reverse=True)
        
        # Wenn die beste Übereinstimmung gut genug ist, diese zurückgeben
        if similarities and similarities[0][0] > 0.6:
            return similarities[0][1]
        
        return None
    
    @commands.hybrid_command(name="fragebot", description="Stelle eine Frage über den Bot")
    async def ask_question(self, ctx: commands.Context, *, frage: str):
        """
        Stelle eine Frage über den Bot und erhalte eine Antwort.
        
        Args:
            frage: Die Frage, die du stellen möchtest
        """
        await self._process_question(ctx, frage)
    
    async def _process_question(self, ctx, query: str):
        """Verarbeitet eine Frage und gibt eine Antwort zurück."""
        faq = self._find_similar_question(query)
        
        if faq:
            # Erstelle ein schönes Embed für die Antwort
            embed = discord.Embed(
                title=f"❓ {faq['question']}",
                description=faq['answer'],
                color=discord.Color.blue()
            )
            
            # Füge Kategorie hinzu
            if "category" in faq:
                embed.add_field(
                    name="Kategorie",
                    value=faq["category"],
                    inline=True
                )
            
            # Füge verwandte Fragen hinzu, wenn vorhanden
            related_faqs = []
            for other_faq in self.faqs["faqs"]:
                if other_faq != faq and other_faq.get("category") == faq.get("category"):
                    related_faqs.append(other_faq)
            
            if related_faqs:
                # Wähle bis zu 2 zufällige verwandte Fragen
                sample_size = min(2, len(related_faqs))
                random_related = random.sample(related_faqs, sample_size)
                
                related_questions = "\n".join([f"• {q['question']}" for q in random_related])
                embed.add_field(
                    name="Verwandte Fragen",
                    value=related_questions,
                    inline=False
                )
            
            # Füge Hinweis hinzu, wie man weitere Fragen stellt
            embed.set_footer(text=f"Du kannst weitere Fragen mit /fragebot stellen")
            
            await ctx.send(embed=embed)
        else:
            # Keine passende Frage gefunden
            embed = discord.Embed(
                title="❓ Unbekannte Frage",
                description=f"Leider konnte ich keine Antwort auf deine Frage finden: '{query}'",
                color=discord.Color.orange()
            )
            
            # Liste einige Beispielfragen auf
            sample_faqs = random.sample(self.faqs["faqs"], min(3, len(self.faqs["faqs"])))
            examples = "\n".join([f"• {faq['question']}" for faq in sample_faqs])
            
            embed.add_field(
                name="Probiere diese Fragen aus",
                value=examples,
                inline=False
            )
            
            # Ticket-System als Alternative vorschlagen
            embed.add_field(
                name="Weitere Hilfe benötigt?",
                value="Wenn du eine spezifische Frage hast, die nicht beantwortet wurde, erstelle bitte ein Ticket mit `/createticket`. Ein Team-Mitglied wird dir dann persönlich helfen.",
                inline=False
            )
            
            embed.add_field(
                name="Noch mehr Hilfe",
                value="Du kannst auch `/help` verwenden, um mehr über die Befehle des Bots zu erfahren.",
                inline=False
            )
            
            embed.set_footer(text="Frage etwas spezifischer oder versuche es mit anderen Worten.")
            
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="allfragen", description="Zeigt alle verfügbaren FAQ-Kategorien an")
    @commands.has_permissions(administrator=True)
    async def show_all_categories(self, ctx: commands.Context):
        """
        Zeigt alle verfügbaren FAQ-Kategorien an.
        Diese können dann mit dem /kategorie Befehl angezeigt werden.
        Nur für Administratoren.
        """
        # Sammle alle einzigartigen Kategorien
        categories = set()
        for faq in self.faqs["faqs"]:
            if "category" in faq:
                categories.add(faq["category"])
        
        # Erstelle ein Embed mit allen Kategorien
        embed = discord.Embed(
            title="📚 Verfügbare FAQ-Kategorien",
            description="Hier sind alle verfügbaren Kategorien von Fragen, die der Bot beantworten kann:",
            color=discord.Color.blue()
        )
        
        categories_list = "\n".join([f"• `{category}`" for category in sorted(categories)])
        embed.add_field(
            name="Kategorien",
            value=categories_list,
            inline=False
        )
        
        embed.add_field(
            name="Wie verwenden?",
            value="Verwende `/kategorie [Kategoriename]`, um alle Fragen in einer bestimmten Kategorie anzuzeigen.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="kategorie", description="Zeigt alle Fragen einer bestimmten Kategorie an")
    @app_commands.describe(kategorie="Der Name der Kategorie, deren Fragen angezeigt werden sollen")
    async def show_category(self, ctx: commands.Context, *, kategorie: str):
        """
        Zeigt alle Fragen einer bestimmten Kategorie an.
        
        Args:
            kategorie: Der Name der Kategorie, deren Fragen angezeigt werden sollen
        """
        # Finde alle Fragen in der angegebenen Kategorie
        category_faqs = []
        for faq in self.faqs["faqs"]:
            if faq.get("category", "").lower() == kategorie.lower():
                category_faqs.append(faq)
        
        if not category_faqs:
            # Keine Fragen in dieser Kategorie gefunden
            embed = discord.Embed(
                title="❌ Unbekannte Kategorie",
                description=f"Leider konnte ich keine Fragen in der Kategorie '{kategorie}' finden.",
                color=discord.Color.red()
            )
            
            # Alle verfügbaren Kategorien auflisten
            categories = set()
            for faq in self.faqs["faqs"]:
                if "category" in faq:
                    categories.add(faq["category"])
            
            if categories:
                categories_list = ", ".join([f"`{category}`" for category in sorted(categories)])
                embed.add_field(
                    name="Verfügbare Kategorien",
                    value=categories_list,
                    inline=False
                )
            
            await ctx.send(embed=embed)
            return
        
        # Erstelle ein Embed mit allen Fragen in der Kategorie
        embed = discord.Embed(
            title=f"📚 Fragen zur Kategorie: {kategorie}",
            description=f"Hier sind alle Fragen in der Kategorie '{kategorie}':",
            color=discord.Color.blue()
        )
        
        # Füge jede Frage als Feld hinzu
        for i, faq in enumerate(category_faqs):
            embed.add_field(
                name=f"{i+1}. {faq['question']}",
                value=faq['answer'][:100] + ("..." if len(faq['answer']) > 100 else ""),
                inline=False
            )
        
        embed.add_field(
            name="Wie verwenden?",
            value="Verwende `/fragebot [Deine Frage]`, um eine bestimmte Frage zu stellen.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="addfaq", description="Fügt eine neue FAQ hinzu")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        frage="Die Frage, die hinzugefügt werden soll",
        antwort="Die Antwort auf die Frage",
        kategorie="Die Kategorie, zu der die Frage gehört",
        aliase="Kommagetrennte Liste von alternativen Formulierungen der Frage"
    )
    async def add_faq(
        self, 
        ctx: commands.Context, 
        frage: str, 
        antwort: str, 
        kategorie: str, 
        aliase: str = ""
    ):
        """
        Fügt eine neue FAQ hinzu. Nur für Administratoren.
        
        Args:
            frage: Die Frage, die hinzugefügt werden soll
            antwort: Die Antwort auf die Frage
            kategorie: Die Kategorie, zu der die Frage gehört
            aliase: Kommagetrennte Liste von alternativen Formulierungen der Frage
        """
        # Aliase verarbeiten
        aliases_list = [a.strip() for a in aliase.split(",")] if aliase else []
        aliases_list = [a for a in aliases_list if a]  # Leere Einträge entfernen
        
        # Neue FAQ erstellen
        new_faq = {
            "question": frage,
            "answer": antwort,
            "category": kategorie,
            "aliases": aliases_list
        }
        
        # FAQ hinzufügen
        self.faqs["faqs"].append(new_faq)
        self._save_faqs(self.faqs)
        
        # Bestätigung senden
        embed = discord.Embed(
            title="✅ FAQ hinzugefügt",
            description=f"Die Frage wurde erfolgreich hinzugefügt!",
            color=discord.Color.green()
        )
        
        embed.add_field(name="Frage", value=frage, inline=False)
        embed.add_field(name="Antwort", value=antwort[:100] + ("..." if len(antwort) > 100 else ""), inline=False)
        embed.add_field(name="Kategorie", value=kategorie, inline=True)
        
        if aliases_list:
            embed.add_field(name="Aliase", value=", ".join(aliases_list), inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="removefaq", description="Entfernt eine FAQ")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(frage="Die Frage, die entfernt werden soll")
    async def remove_faq(self, ctx: commands.Context, *, frage: str):
        """
        Entfernt eine FAQ. Nur für Administratoren.
        
        Args:
            frage: Die Frage, die entfernt werden soll
        """
        # Suche nach der Frage
        found = False
        for i, faq in enumerate(self.faqs["faqs"]):
            if faq["question"].lower() == frage.lower():
                self.faqs["faqs"].pop(i)
                found = True
                break
        
        if found:
            # FAQ entfernen und speichern
            self._save_faqs(self.faqs)
            
            embed = discord.Embed(
                title="✅ FAQ entfernt",
                description=f"Die Frage '{frage}' wurde erfolgreich entfernt!",
                color=discord.Color.green()
            )
            
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ FAQ nicht gefunden",
                description=f"Die Frage '{frage}' konnte nicht gefunden werden.",
                color=discord.Color.red()
            )
            
            await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="setupassistant", description="Richtet einen Kanal für den Bot-Assistenten ein")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(channel="Der Kanal, in dem der Bot automatisch auf Fragen antworten soll")
    async def setup_assistant(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Richtet einen Kanal für den Bot-Assistenten ein. In diesem Kanal wird der Bot automatisch auf Fragen antworten,
        ohne dass ein Befehl verwendet werden muss.
        
        Args:
            channel: Der Kanal, in dem der Bot automatisch antworten soll. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
        """
        # Wenn kein Kanal angegeben ist, verwende den aktuellen Kanal
        if channel is None:
            channel = ctx.channel
        
        # Speichere den Kanal in der Konfiguration
        guild_id = str(ctx.guild.id)
        channel_id = channel.id
        
        # Initialisiere guild_id in assistant_channels, falls es nicht existiert
        if guild_id not in self.faqs["assistant_channels"]:
            self.faqs["assistant_channels"][guild_id] = []
        
        # Überprüfe, ob der Kanal bereits hinzugefügt wurde
        if channel_id in self.faqs["assistant_channels"][guild_id]:
            embed = discord.Embed(
                title="❌ Kanal bereits eingerichtet",
                description=f"Der Kanal {channel.mention} ist bereits als Assistenten-Kanal eingerichtet.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Füge den Kanal hinzu
        self.faqs["assistant_channels"][guild_id].append(channel_id)
        self._save_faqs(self.faqs)
        
        # Sende eine Willkommensnachricht in den Kanal
        welcome_embed = discord.Embed(
            title="🤖 Bot-Assistent aktiviert!",
            description=(
                f"In diesem Kanal kannst du nun direkt Fragen stellen, ohne einen Befehl zu verwenden!\n\n"
                f"Der Bot wird automatisch auf deine Fragen antworten. Frage einfach alles, was du über den Bot wissen möchtest."
            ),
            color=discord.Color.blue()
        )
        
        welcome_embed.add_field(
            name="📋 Beispielfragen",
            value=(
                "• Wie funktioniert das Level-System?\n"
                "• Was kann dieser Bot alles?\n"
                "• Wie erstelle ich ein Ticket?\n"
                "• Wie bekomme ich Rollen?"
            ),
            inline=False
        )
        
        welcome_embed.set_footer(text="Du kannst jederzeit mehr Fragen stellen!")
        
        await channel.send(embed=welcome_embed)
        
        # Bestätige dem Admin die Einrichtung
        embed = discord.Embed(
            title="✅ Assistenten-Kanal eingerichtet",
            description=f"Der Kanal {channel.mention} wurde erfolgreich als Assistenten-Kanal eingerichtet.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Verwendung",
            value="In diesem Kanal können Benutzer jetzt direkt Fragen stellen, ohne einen Befehl zu verwenden.",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="removeassistant", description="Entfernt den Bot-Assistenten aus einem Kanal")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(channel="Der Kanal, aus dem der Bot-Assistent entfernt werden soll")
    async def remove_assistant(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Entfernt den Bot-Assistenten aus einem Kanal.
        
        Args:
            channel: Der Kanal, aus dem der Bot-Assistent entfernt werden soll. Wenn keiner angegeben ist, wird der aktuelle Kanal verwendet.
        """
        # Wenn kein Kanal angegeben ist, verwende den aktuellen Kanal
        if channel is None:
            channel = ctx.channel
        
        # Entferne den Kanal aus der Konfiguration
        guild_id = str(ctx.guild.id)
        channel_id = channel.id
        
        # Überprüfe, ob der Server in der Konfiguration existiert
        if guild_id not in self.faqs["assistant_channels"]:
            embed = discord.Embed(
                title="❌ Kein Assistent aktiv",
                description="Der Bot-Assistent wurde für diesen Server nicht eingerichtet.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Überprüfe, ob der Kanal als Assistenten-Kanal eingerichtet ist
        if channel_id not in self.faqs["assistant_channels"][guild_id]:
            embed = discord.Embed(
                title="❌ Kein Assistent in diesem Kanal",
                description=f"Der Kanal {channel.mention} ist nicht als Assistenten-Kanal eingerichtet.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Entferne den Kanal
        self.faqs["assistant_channels"][guild_id].remove(channel_id)
        
        # Wenn keine Kanäle mehr für diesen Server existieren, entferne den Server aus der Konfiguration
        if not self.faqs["assistant_channels"][guild_id]:
            del self.faqs["assistant_channels"][guild_id]
        
        self._save_faqs(self.faqs)
        
        # Bestätige dem Admin die Entfernung
        embed = discord.Embed(
            title="✅ Assistenten-Kanal entfernt",
            description=f"Der Bot-Assistent wurde erfolgreich aus dem Kanal {channel.mention} entfernt.",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="listassistant", description="Zeigt eine Liste aller Assistenten-Kanäle an")
    @commands.has_permissions(administrator=True)
    async def list_assistant(self, ctx: commands.Context):
        """
        Zeigt eine Liste aller Kanäle an, in denen der Bot-Assistent aktiv ist.
        """
        guild_id = str(ctx.guild.id)
        
        # Überprüfe, ob der Server in der Konfiguration existiert
        if guild_id not in self.faqs["assistant_channels"] or not self.faqs["assistant_channels"][guild_id]:
            embed = discord.Embed(
                title="❌ Keine Assistenten-Kanäle",
                description="Es wurden keine Assistenten-Kanäle für diesen Server eingerichtet.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Erstelle eine Liste aller Assistenten-Kanäle
        channel_mentions = []
        for channel_id in self.faqs["assistant_channels"][guild_id]:
            channel = ctx.guild.get_channel(channel_id)
            if channel:
                channel_mentions.append(channel.mention)
        
        # Erstelle ein Embed mit allen Assistenten-Kanälen
        embed = discord.Embed(
            title="📋 Assistenten-Kanäle",
            description="Hier sind alle Kanäle, in denen der Bot-Assistent aktiv ist:",
            color=discord.Color.blue()
        )
        
        if channel_mentions:
            embed.add_field(
                name="Aktive Kanäle",
                value="\n".join(channel_mentions),
                inline=False
            )
        else:
            embed.add_field(
                name="Aktive Kanäle",
                value="Keine Kanäle gefunden. Möglicherweise wurden die Kanäle gelöscht.",
                inline=False
            )
        
        await ctx.send(embed=embed)

    async def on_message(self, message):
        """Event-Handler für Nachrichten in Assistenten-Kanälen."""
        # Ignoriere Nachrichten von Bots, um Endlosschleifen zu vermeiden
        if message.author.bot:
            return
        
        # Überprüfe, ob der Kanal ein Assistenten-Kanal ist
        guild_id = str(message.guild.id) if message.guild else None
        channel_id = message.channel.id
        
        # Wenn keine Guild (DM) oder kein Assistenten-Kanal, ignoriere die Nachricht
        if not guild_id or guild_id not in self.faqs["assistant_channels"] or channel_id not in self.faqs["assistant_channels"][guild_id]:
            return
        
        # Extrahiere die Frage aus der Nachricht
        query = message.content.strip()
        
        # Ignoriere leere Nachrichten oder einzelne Zeichen
        if len(query) < 3:
            return
        
        # Reagiere mit dem Denk-Emoji, um zu zeigen, dass der Bot die Anfrage verarbeitet
        try:
            await message.add_reaction('🤔')
        except:
            pass  # Ignoriere Fehler, falls keine Berechtigung zum Hinzufügen von Reaktionen
        
        # Verarbeite die Frage
        ctx = await self.bot.get_context(message)
        await self._process_question(ctx, query)
        
        # Entferne die Denk-Reaktion und füge eine häkchen-Reaktion hinzu
        try:
            await message.remove_reaction('🤔', self.bot.user)
            await message.add_reaction('✅')
        except:
            pass  # Ignoriere Fehler bei Reaktionen

async def setup(bot: commands.Bot):
    """Füge den BotAssistant-Cog zum Bot hinzu."""
    await bot.add_cog(BotAssistant(bot))
    logger.info("BotAssistant cog loaded")