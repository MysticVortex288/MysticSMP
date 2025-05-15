# Architecture

## Overview

This repository contains a multi-functional Discord bot built with discord.py. The bot provides various features such as invite tracking, level systems, ticket management, temporary voice channels, verification, content announcements, and self-roles. The application consists of two main components: the Discord bot and a web server (Flask) that provides API endpoints for bot management and keeps the bot alive.

## System Architecture

The system follows a modular architecture organized around cogs (Discord.py's extension system). Each functional aspect of the bot is implemented as a separate cog, making the codebase maintainable and extensible.

```
┌─────────────────────────┐
│                         │
│    Discord Bot (main)   │
│                         │
└───────────┬─────────────┘
            │
            │ initializes
            ▼
┌─────────────────────────┐      ┌─────────────────────────┐
│                         │      │                         │
│     Functional Cogs     │◄────►│    Utility Services     │
│                         │      │                         │
└───────────┬─────────────┘      └─────────────────────────┘
            │                          │
            │ reads/writes             │ provides
            ▼                          ▼
┌─────────────────────────┐      ┌─────────────────────────┐
│                         │      │                         │
│     JSON Data Files     │      │  Configuration Services │
│                         │      │                         │
└─────────────────────────┘      └─────────────────────────┘
            ▲
            │ exposed via
            │
┌─────────────────────────┐
│                         │
│     Web API (Flask)     │
│                         │
└─────────────────────────┘
```

## Key Components

### 1. Discord Bot (main.py, bot.py)
- Entry point for the application
- Initializes bot configuration
- Loads cogs and sets up event handlers
- Connects to Discord API

### 2. Cogs (cogs/ directory)
Each cog represents a specific feature set:

- **InviteTracker**: Tracks who invited whom to the server
- **LevelSystem**: User experience points and level progression system
- **TicketSystem**: Support ticket creation and management
- **TempVoice**: Temporary voice channel creation
- **ContentAnnouncer**: Announces content from platforms like TikTok
- **SelfRoles**: Role assignment through buttons
- **ServerStats**: Server statistics display
- **Verification**: User verification system
- **CountingGame**: Simple counting game implementation
- **ChannelLocker**: Time-based channel locking
- **BotAssistant**: FAQ answering system for bot-related questions
- **WelcomeMessages**: Customizable welcome messages
- **LanguageSettings**: Language preferences management
- **HelpCommands**: Help system implementation

### 3. Utility Services (utils/ directory)
- **ConfigManager**: Configuration management and persistence
- **EmbedCreator**: Discord embed creation helpers
- **LanguageManager**: Multi-language support

### 4. Web API (keep_alive.py, bot_panel_api.py)
- Flask web server providing status endpoints
- REST API for bot management through external panels
- Serves as a "keep-alive" mechanism to prevent the bot from sleeping

### 5. Data Storage
- Uses JSON files for persistence (no database)
- Each functional area typically has its own JSON file
- File-based approach suitable for the scale of the application

## Data Flow

1. **User Command Flow**:
   - User sends a command in Discord
   - Bot processes the command through the appropriate cog
   - Cog retrieves/updates configuration from JSON files
   - Bot responds with appropriate Discord message/embed

2. **Event-Driven Flow**:
   - Discord events (e.g., member joins, messages) trigger event listeners
   - Event handlers in cogs process the events
   - State updates are persisted to JSON files

3. **API Flow**:
   - External requests come to the Flask API
   - API validates authentication (API key)
   - API retrieves or updates bot state
   - API returns JSON response

## External Dependencies

### Discord.py
- Primary framework for Discord API interaction
- Handles events, commands, and message processing

### Flask
- Web server framework for the API endpoints
- Provides "keep-alive" functionality

### Third-Party Services
- **TikTok**: Content monitoring for announcements
- **YouTube/Twitch**: Content monitoring (referenced but not fully implemented)

### Other Libraries
- **requests**: HTTP requests for external APIs
- **BeautifulSoup4/trafilatura**: Web scraping for content monitoring
- **yt-dlp**: YouTube video downloading for music functionality
- **spotipy**: Spotify API client (referenced in code)

## Deployment Strategy

The application is configured for deployment on Replit with the following components:

1. **Replit Deployment**:
   - Uses Nix for package management
   - Configured with Python 3.11 runtime
   - Includes system dependencies (ffmpeg, libsodium, openssl, postgresql)

2. **Web Server**:
   - Gunicorn serves the Flask application
   - Listens on port 5000 (mapped to port 80 externally)

3. **Configuration Management**:
   - Environment variables for sensitive data (Discord token)
   - .env file for local development
   - Replit Secrets for production environment variables

4. **Keep-Alive Mechanism**:
   - Flask server running on port 8080
   - Prevents Replit from sleeping due to inactivity

5. **Workflow Configuration**:
   - Parallel execution of Discord bot and web server
   - Run button configured for easy startup
   - Automatic reloading for development purposes

## Security Considerations

1. **API Authentication**:
   - Uses API key authentication for bot panel access
   - Supports key in headers or query parameters

2. **Discord Permissions**:
   - Bot requires specific Discord permissions (detailed in documentation)
   - Admin commands check for appropriate permissions

3. **Environment Variables**:
   - Sensitive data stored in environment variables
   - .env.example provides a template without real values