# Discord Bot Anleitung

## Übersicht der Funktionen

Dieser Discord-Bot bietet folgende Funktionen:

1. **Einladungsverfolgung**: Verfolgt, wer wen zum Server eingeladen hat
2. **Willkommensnachrichten**: Personalisierte Nachrichten und Bilder für neue Mitglieder
3. **Levelsystem**: XP und Level für Mitglieder mit Rollen-Belohnungen
4. **Ticketsystem**: Support-Tickets mit benutzerdefinierten Panels
5. **Zählspiel**: Einfaches Spiel zum gemeinsamen Zählen mit Highscore
6. **Temporäre Sprachkanäle**: Erstellt temporäre Sprachkanäle für Nutzer
7. **Verifizierung**: Button-basiertes System zur Verifizierung neuer Mitglieder
8. **Content-Ankündiger**: Erkennt und kündigt Social-Media-Inhalte an
9. **Selbstzuweisbare Rollen**: Panel für Mitglieder, um Rollen zu erhalten
10. **Bot-Assistent**: Beantwortet Fragen über den Bot
11. **Server-Statistik**: Zeigt Statistiken in Kanalnamen an
12. **Mehrsprachig**: Unterstützt Deutsch und Englisch
13. **Kanalsperre**: Sperrt Kanäle für bestimmte Zeiträume
14. **Emoji-Stealer**: Kopiert Emojis von anderen Servern
15. **Captcha-Verifizierung**: Zusätzliche Sicherheit gegen Bot-Accounts
16. **Moderation**: Befehle für Server-Moderation mit DM-Benachrichtigungen
17. **Wirtschaftssystem**: Virtuelle Währung und Befehle wie daily, work, pay, rob
18. **Web-Dashboard**: Konfiguration aller Bot-Funktionen über eine Website

## Installation

1. Lade die ZIP-Datei herunter und entpacke sie
2. Erstelle eine `.env`-Datei mit folgenden Einträgen:
   ```
   DISCORD_TOKEN=dein_discord_bot_token
   DISCORD_CLIENT_ID=dein_discord_client_id
   DISCORD_CLIENT_SECRET=dein_discord_client_secret
   ```
3. Installiere die erforderlichen Pakete:
   ```
   pip install -r packages_list.txt
   ```
4. Starte den Bot:
   ```
   python main.py
   ```

## Befehle und Funktionen

### Moderation
- `/kick`: Kickt ein Mitglied
- `/ban`: Bannt ein Mitglied
- `/tempban`: Bannt ein Mitglied temporär
- `/warn`: Verwarnt ein Mitglied
- `/mute`: Schaltet ein Mitglied stumm
- `/unmute`: Hebt die Stummschaltung auf
- `/clear`: Löscht Nachrichten

### Wirtschaft
- `/daily`: Tägliche Belohnung
- `/work`: Arbeiten für Geld
- `/balance`: Kontostand anzeigen
- `/pay`: Geld an andere Mitglieder senden
- `/rob`: Versuche Geld zu stehlen
- `/beg`: Betteln für Geld
- `/eco-settings`: Wirtschaftseinstellungen konfigurieren

### Selbstzuweisbare Rollen
- `/setup-roles`: Richtet Rollen-Panel ein
- `/add-role-button`: Fügt Rollenknopf hinzu
- `/remove-role-button`: Entfernt Rollenknopf

### Levelsystem
- `/rank`: Zeigt deinen Rang an
- `/leaderboard`: Zeigt die Rangliste an
- `/add-level-reward`: Fügt Belohnung für Level hinzu
- `/remove-level-reward`: Entfernt Belohnung

### Tickets
- `/setup-tickets`: Richtet Ticketsystem ein
- `/close-ticket`: Schließt ein Ticket
- `/add-support-role`: Fügt Support-Rolle hinzu

### Temporäre Sprachkanäle
- `/setup-tempvoice`: Richtet temporäre Sprachkanäle ein
- `/add-tempvoice-category`: Fügt neue Kategorie hinzu

## Bot-Konfiguration

Die Konfiguration erfolgt über Discord-Befehle oder das Web-Dashboard.

Beispiele für Konfigurationsbefehle:
- `/setup welcome`: Konfiguriert Willkommensnachrichten
- `/setup verification`: Richtet Verifizierungssystem ein
- `/setup counting`: Konfiguriert das Zählspiel
- `/setup stats`: Richtet Server-Statistiken ein
- `/setup assistant`: Konfiguriert den Bot-Assistenten

## Support und Hilfe

Für Hilfe stehen folgende Ressourcen zur Verfügung:
- `/help`: Zeigt allgemeine Hilfe an
- `/help [Modul]`: Zeigt Hilfe für ein spezifisches Modul an
- Bot-Assistent: Beantwortet Fragen in speziellen Kanälen
- Web-Dashboard: Bietet grafische Konfigurationsmöglichkeiten

## Fehlerbehebung

Häufige Probleme und Lösungen:
1. **Bot reagiert nicht auf Befehle**: Überprüfe die Bot-Berechtigungen
2. **Fehler bei Bilderzeugung**: Installiere Pillow korrekt mit pip
3. **Datenbankfehler**: Stelle sicher, dass die JSON-Dateien beschreibbar sind
4. **API-Fehler**: Überprüfe, ob alle erforderlichen API-Schlüssel in der .env-Datei vorhanden sind