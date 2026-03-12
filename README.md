# Nextcord Starter Kit

A beginner-friendly Discord bot starter framework built with **Nextcord**, featuring a modular cog system, Twitch live alerts, and GitHub-powered data updates.

This repository is designed to provide a **clean starting point** for building Discord bots without unnecessary complexity.

---

## Features

- Modular **cog-based architecture**
- Slash command support using **Nextcord 3.X.X**
- Twitch live notifications
- GitHub auto-updater for data files
- Simple `.env` configuration
- Cross-platform startup scripts (`start.sh` / `start.bat`)
- Optional community cogs support

---

## Requirements

- Python **3.12 or newer**
- A **Discord bot token**
- Git (optional, used for the auto-updater)
- Twitch API credentials (only required if using the Twitch cog)

---

## Quick Start

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/Nextcord-Starter-Kit.git
cd Nextcord-Starter-Kit
```

Create your configuration file:

Linux / macOS:

```bash
cp example.env .env
```

Windows:

```bat
copy example.env .env
```

Edit `.env` and fill in the required values.

Start the bot:

### Linux / macOS

```bash
chmod +x start.sh
./start.sh
```

(chmod +x start.sh only needs to be done once)

### Windows

```bat
start.bat
```

---

## Project Structure

```
Nextcord-Starter-Kit
│
├── cogs/                # Core cogs loaded by the bot
│   ├── server.py
│   ├── start.py
│   └── status.py
│
├── cogs-optional/       # Optional or community-contributed cogs
│   ├── autoupdater.py
│   ├── responder.py
│   ├── twitch.py
│   └── user.py
│
├── data/                # Data files used by the bot
│   ├── assets (folder)
│   ├── twitch_cog_files (Folder, populated from the Nexic Data Repo)
│   ├── bot_status.json (File, from the Nexic Data Repo)
│   └── user_responses.json
│
├── bot.py
├── requirements.txt
├── example.env
├── start.bat
└── start.sh
```

---

## Core vs Optional Cogs

The repository separates cogs into two categories:

### `cogs/`
Contains **core functionality** required for the starter bot.

These cogs are expected to work with the default configuration.

### `cogs-optional/`
Contains **optional or community-contributed cogs** that are not loaded by default.

To enable one:

1. Move the file into the `cogs/` folder
2. Restart the bot or reload the cog

Some optional cogs may require additional dependencies.

---

## Configuration

All configuration is handled through the `.env` file.

Required variables include:

- `BOT_TOKEN`
- `GUILD_ID`
- `OWNER_ID`
- `COG_CODE`
- `COG_DIR`

Optional features such as Twitch notifications and the GitHub auto-updater require additional variables.

---

## Contributing

Contributions are welcome!

Examples of helpful contributions:

- New optional cogs
- Documentation improvements
- Bug fixes
- Code improvements
- Example implementations

Please read **CONTRIBUTING.md** before submitting pull requests.

---

## Security

Never commit sensitive information such as:

- `.env` files
- Discord bot tokens
- API keys
- GitHub access tokens

The repository includes `example.env` as a safe configuration template.

---

## License

This project is licensed under the **MIT License**.
