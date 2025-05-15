# Bot Panel Anleitung

Diese Anleitung erklärt, wie du deinen Discord-Bot mit botpanel.gg verbinden kannst, um ein benutzerfreundliches Web-Interface zur Verwaltung deines Bots zu erhalten.

## Voraussetzungen

1. Ein aktiver Discord-Bot (bereits vorhanden)
2. Ein Konto bei botpanel.gg
3. Ein API-Schlüssel für die Kommunikation zwischen dem Bot und dem Panel

## Schritt 1: Konto bei botpanel.gg erstellen

1. Besuche [botpanel.gg](https://botpanel.gg) und erstelle ein Konto
2. Bestätige deine E-Mail-Adresse und melde dich an
3. Navigiere zum Dashboard und klicke auf "Neues Panel erstellen"

## Schritt 2: API-Schlüssel generieren

1. In deinem botpanel.gg Dashboard, gehe zu "Einstellungen" > "API"
2. Klicke auf "Neuen API-Schlüssel generieren"
3. Kopiere den generierten Schlüssel

## Schritt 3: API-Schlüssel im Bot einrichten

### Option 1: Mit .env Datei (empfohlen)

1. Öffne die Datei `.env` in deinem Bot-Projekt
2. Füge die folgende Zeile hinzu:
   ```
   BOT_PANEL_API_KEY=dein_api_schluessel_hier
   ```
3. Ersetze `dein_api_schluessel_hier` mit dem kopierten API-Schlüssel von botpanel.gg

### Option 2: Mit Umgebungsvariablen in Replit

1. Gehe in deinem Replit-Projekt zu "Secrets" im linken Menü
2. Füge einen neuen Secret hinzu:
   - Schlüssel: `BOT_PANEL_API_KEY`
   - Wert: Dein API-Schlüssel von botpanel.gg

## Schritt 4: Bot in botpanel.gg registrieren

1. Im botpanel.gg Dashboard, klicke auf "Bot hinzufügen"
2. Gib die folgenden Informationen ein:
   - Bot-Name: [Name deines Bots]
   - Bot-ID: [Die Client-ID deines Discord-Bots]
   - API-Endpunkt: `https://dein-replit-projekt.repl.co/api`
   - API-Schlüssel: [Der gleiche Schlüssel, den du in Schritt 3 konfiguriert hast]

## Schritt 5: Starte deinen Bot neu

1. Starte deinen Bot neu, um die Änderungen zu übernehmen
2. Überprüfe die Logs auf Meldungen wie "Bot API initialisiert" und "Web-Server gestartet"

## Schritt 6: Panel konfigurieren

1. Gehe zurück zu botpanel.gg und navigiere zu deinem Panel
2. Konfiguriere die Module und Features, die du in deinem Panel haben möchtest:
   - Server-Management
   - Nachrichten senden
   - Statistiken anzeigen
   - Einstellungen ändern
   - und mehr...

## Überprüfung der API-Verbindung

Um zu testen, ob die API-Verbindung funktioniert:

1. Besuche `https://dein-replit-projekt.repl.co/api` in deinem Browser
2. Du solltest Informationen über die verfügbaren API-Endpunkte sehen
3. Wenn du `https://dein-replit-projekt.repl.co/status` besuchst, solltest du den Status deines Bots sehen

## Fehlerbehebung

Wenn du Probleme bei der Verbindung des Panels mit deinem Bot hast:

1. **API-Schlüssel überprüfen:** Stelle sicher, dass der API-Schlüssel in beiden Systemen übereinstimmt
2. **URL überprüfen:** Stelle sicher, dass die API-URL korrekt ist und dein Replit-Projekt läuft
3. **Logs überprüfen:** Schaue in den Bot-Logs nach Fehlermeldungen
4. **Firewalls:** Stelle sicher, dass keine Firewall den Traffic blockiert

## Sicherheitshinweise

- Teile deinen API-Schlüssel mit niemandem
- Verwende einen starken, eindeutigen Schlüssel
- Ändere deinen API-Schlüssel regelmäßig, um die Sicherheit zu erhöhen

Bei Fragen oder Problemen kannst du die Dokumentation von botpanel.gg konsultieren oder den Support kontaktieren.

## Erweiterungsmöglichkeiten

In der Zukunft könntest du die API und das Panel um folgende Funktionen erweitern:

- Benutzerdefinierte Befehle erstellen
- Erweiterte Statistiken und Analysen
- Automatisierte Aktionen einrichten
- Mehrsprachige Unterstützung aktivieren
- Und vieles mehr!