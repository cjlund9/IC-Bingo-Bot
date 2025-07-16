# IC-Bingo-Bot

A Discord bot for managing RuneScape bingo games with team-based progress tracking and automated board generation.

## Features

- **Team-based Progress Tracking**: Separate progress tracking for multiple teams
- **Automated Board Generation**: Real-time board images showing completion status
- **Submission System**: Screenshot-based submissions with approval workflow
- **Database-backed Storage**: Robust SQLite database for all progress and submissions
- **Admin Controls**: Comprehensive admin commands for managing the event
- **Rate Limiting**: Built-in rate limiting to prevent spam

## Commands

### User Commands
- `/submit` - Submit a completed bingo tile with screenshot
- `/progress` - View progress for your team or specific tile
- `/board` - Display the current bingo board (leadership/event coordinator only)

### Admin Commands
- `/migrate_to_db` - Migrate tiles from JSON to database (Admin only)
- `/clear_progress` - Clear all team progress and submissions (Admin only)
- `/manage` - Manage submissions and progress (Admin only)
- `/stats` - Show detailed statistics for all teams
- `/leaderboard` - Show team leaderboard

## File Structure

```
ic-bot/
├── main.py                 # Main bot entry point
├── config.py              # Configuration settings
├── storage.py             # Database-backed progress functions
├── board.py               # Board image generation
├── database.py            # Database management
├── leaderboard.db         # SQLite database (all progress data)
├── commands/              # Discord command modules
│   ├── submit.py          # Submission command
│   ├── board_cmd.py       # Board display command
│   ├── progress.py        # Progress tracking command
│   ├── manage.py          # Admin management command
│   └── sync.py            # Database management commands
├── views/                 # Discord UI components
│   ├── approval.py        # Submission approval view
│   ├── hold.py            # Hold review view
│   └── submission_management.py
├── utils/                 # Utility functions
├── data/
│   └── tiles.json         # Tile definitions (name, drops, etc.)
└── assets/                # Images, fonts, etc.
```

## Database Schema

The bot uses a SQLite database (`leaderboard.db`) with the following tables:

### bingo_tiles
- `id` - Primary key, tile index
- `name` - Tile name
- `drops_needed` - Number of drops required to complete
- `drops_required` - JSON array of specific drops that count
- `created_at` - Timestamp

### bingo_submissions
- `id` - Primary key
- `team` - Team name
- `tile_id` - Foreign key to bingo_tiles
- `user_id` - Discord user ID
- `drop_name` - Name of the drop submitted
- `quantity` - Quantity submitted
- `submitted_at` - Timestamp

### bingo_team_progress
- `id` - Primary key
- `team` - Team name
- `tile_id` - Foreign key to bingo_tiles
- `completed_count` - Current progress count
- `total_required` - Total drops needed
- `last_updated` - Timestamp

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   Create a `.env` file with:
   ```
   DISCORD_BOT_TOKEN=your_bot_token
   LEADERSHIP_ROLE=leadership
   EVENT_COORDINATOR_ROLE=event_coordinator
   ```

3. **Set Up Database**
   ```bash
   python3 setup_database_safeguards.py
   ```

4. **Run the Bot**
   ```bash
   python3 main.py
   ```

## Progress Tracking

All progress data is stored in the SQLite database with automatic consistency checks and foreign key constraints. The system provides:

- **Real-time Updates**: Progress updates immediately reflect on the board
- **Data Integrity**: Foreign key constraints prevent orphaned data
- **Performance**: Indexed queries for fast access
- **Reliability**: ACID compliance for data consistency

## Admin Functions

### Database Management
- **Clear Progress**: Remove all team progress and submissions
- **Migrate Tiles**: Sync tile definitions from JSON to database
- **Validation**: Check database integrity and statistics

### Event Management
- **Submission Approval**: Review and approve/deny submissions
- **Progress Monitoring**: Track team progress and statistics
- **Board Updates**: Generate fresh board images

## Security

- **Role-based Access**: Commands restricted by Discord roles
- **Rate Limiting**: Prevents command spam
- **Input Validation**: All inputs validated before processing
- **Error Handling**: Comprehensive error handling and logging
