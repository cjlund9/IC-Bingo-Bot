# IC-Bingo-Bot
A Discord bot for managing RuneScape bingo games with team-based submissions and approval workflows.

## Features

- 🎯 **Bingo Board Management**: Generate and display bingo boards with progress tracking
- 👥 **Team Support**: Multi-team bingo with role-based access
- 📝 **Submission System**: Submit drops with approval workflow
- ✅ **Progress Tracking**: Visual progress indicators on tiles with detailed statistics
- 🔄 **Hold/Review System**: Hold submissions for review with reason tracking
- 🎨 **Custom Styling**: RuneScape-themed board appearance
- 📊 **Advanced Analytics**: Team leaderboards, progress percentages, and detailed statistics
- 🔧 **Submission Management**: Remove individual submissions and manage tile progress

## Setup

### Prerequisites

- Python 3.8+
- Discord Bot Token
- Discord Server with appropriate channels and roles

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd ic-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

4. **Set up Discord Bot**
   - Create a Discord application at https://discord.com/developers/applications
   - Create a bot and get your token
   - Add the bot to your server with appropriate permissions
   - Set up the required channels and roles

### Configuration

Copy `env.example` to `.env` and configure the following variables:

```env
# Required
DISCORD_BOT_TOKEN=your_bot_token_here

# Optional (defaults shown)
GUILD_ID=your_guild_id
REVIEW_CHANNEL_NAME=submissions
HOLD_REVIEW_CHANNEL_NAME=hold-review
BOARD_CHANNEL_NAME=bingo-board
EVENT_COORDINATOR_ROLE=Event Coordinator
ADMIN_ROLE=Admin
TEAM_ROLES=Moles,Obor
DEFAULT_TEAM=all
```

### Discord Server Setup

1. **Create required channels:**
   - `submissions` - For team submissions
   - `hold-review` - For reviewing held submissions
   - `bingo-board` - For displaying the board

2. **Set up roles:**
   - `Admin` - For administrative commands
   - `Event Coordinator` - For event management
   - Team roles (e.g., `Moles`, `Obor`) - For team members

3. **Configure bot permissions:**
   - Send Messages
   - Attach Files
   - Use Slash Commands
   - Manage Messages (for editing board posts)

## Usage

### Commands

- `/board show [team]` - Display the current bingo board
- `/submit` - Submit a drop for approval
- `/progress [team] [tile]` - View progress for a team or specific tile
- `/leaderboard` - Show team leaderboard (Admin only)
- `/manage <tile> [team]` - Manage submissions for a specific tile (Admin/Event Coordinator only)
- `/stats` - Show detailed statistics for all teams (Admin only)
- `/sync` - Sync completed.json with current tiles.json values (Admin only)
- `/validate` - Validate data and show discrepancies (Admin only)

### Workflow

1. **Team members** submit drops using the `/submit` command
2. **Admins** review submissions and approve/deny/hold them
3. **Held submissions** are moved to the hold-review channel for further review
4. **Board updates** automatically when submissions are approved

## File Structure

```
ic-bot/
├── main.py              # Bot entry point
├── config.py            # Configuration management
├── board.py             # Board generation logic
├── storage.py           # Data persistence
├── commands/            # Discord commands
│   ├── submit.py        # Submission command
│   └── board_cmd.py     # Board display command
├── views/               # Discord UI components
│   ├── approval.py      # Approval buttons
│   ├── hold.py          # Hold functionality
│   └── modals.py        # Input modals
├── assets/              # Static assets
│   └── fonts/           # Custom fonts
└── completed.json       # Progress data
```

## Development

### Running the Bot

```bash
python main.py
```

### Logging

The bot logs to both console and `bot.log` file. Log levels:
- `INFO` - General operations
- `WARNING` - Non-critical issues
- `ERROR` - Errors that need attention

### Data Storage

Progress data is stored in `completed.json` with automatic backups. The file structure:

```json
{
  "team_name": {
    "tile_index": {
      "total_required": 10,
      "completed_count": 5,
      "submissions": [
        {
          "user_id": "123456789",
          "drop": "Fire cape",
          "quantity": 1
        }
      ]
    }
  }
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
