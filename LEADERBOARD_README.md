# Ironclad Events Leaderboard System

A comprehensive Discord bot module for managing event participation, points, leaderboards, and rewards for the Ironclad Events community.

## 🏆 Features

### Points System
- **Competition Points**: Awarded based on placement in various events
- **Collection Log Points**: Points for reaching CLOG tiers
- **Combat Achievement Points**: Points for CA tier submissions
- **Manual Points**: Admin-awarded points for special achievements
- **Audit Trail**: Complete history of all point transactions

### Leaderboard
- **Real-time Rankings**: Live leaderboard with current standings
- **Personal Statistics**: Detailed user stats and history
- **Team Integration**: Points tied to team membership
- **Historical Tracking**: Complete point history and achievements

### Points Shop
- **Item Categories**: Organized shop with different item types
- **Inventory Management**: Limited quantity items with stock tracking
- **Purchase History**: Track all user purchases
- **Admin Management**: Add/remove shop items

### Competition Management
- **Multiple Event Types**: Support for all Ironclad event types
- **Automatic Point Calculation**: Points awarded based on placement
- **Result Tracking**: Complete competition history
- **Admin Controls**: Create and manage competitions

## 📊 Points Structure

### Competition Points
- **"Of the Week" competitions** (Skill, Clue, Boss): 1st (20), 2nd (10), 3rd (5)
- **General Bingo** (2 teams): 1st (20), 2nd (5)
- **Battleship Bingo** (2 teams): 1st (30), 2nd (10)
- **Mania**: 1st (20), 2nd (10), 3rd (5)
- **Bounty**: 1st (10), 2nd (5)

### Collection Log Points
- **Guilded** (1,400): 200 pts
- **Dragon** (1,200): 100 pts
- **Rune** (1,100): 90 pts
- **Adamant** (1,000): 80 pts
- **Mithril** (900): 50 pts
- **Black** (700): 30 pts
- **Steel** (500): 20 pts
- **Iron** (300): 10 pts
- **Bronze** (100): 5 pts

### Combat Achievement Points
- **Grandmaster**: 200 pts
- **Master**: 100 pts
- **Elite**: 75 pts
- **Hard**: 50 pts
- **Medium**: 25 pts
- **Easy**: 10 pts

### Event Buy-in Penalties
- **Non-participation**: Points deducted for missing events
- **Team-based**: Only applies to Moles and Obor team members
- **Flexible amounts**: Configurable penalty amounts per event
- **Audit trail**: All penalties logged with reason and admin

## 🛠️ Setup

### 1. Database Initialization
The system automatically creates a SQLite database (`leaderboard.db`) on first run with all necessary tables and default data.

### 2. Bot Integration
The leaderboard system is integrated into the existing IC Bingo Bot. No additional setup required.

### 3. Permissions
- **Leadership/Event Coordinators**: Full access to all commands
- **Team Members**: View leaderboard, check personal stats, use shop
- **Admins**: All permissions plus database management

## 📋 Commands

### User Commands
- `/iceventleaderboard [limit]` - View the current leaderboard
- `/mystats` - View your personal statistics and history
- `/shop` - Browse the points shop
- `/buy <item_id> [quantity]` - Purchase items from the shop
- `/my_points` - Check your current points balance

### Admin Commands
- `/award_points <points> <reason> [user] [role]` - Award points to a user or all users with a role
- `/icpoints <user> <type> <count/tier> [notes]` - Submit collection log or combat achievement points
- `/event_penalty <event_name> <penalty_amount> [participants_role] [non_participants]` - Apply buy-in penalty to non-participants
- `/add_shop_item <name> <description> <cost> [category] [quantity]` - Add shop item
- `/remove_shop_item <item_id>` - Remove shop item

## 🗄️ Database Schema

### Core Tables
- **users**: User profiles and point totals
- **point_transactions**: Complete audit trail of all point changes
- **competition_types**: Available competition types
- **competitions**: Individual competition instances
- **competition_results**: Competition placements and points
- **clog_tiers**: Collection log tier definitions
- **clog_submissions**: CLOG progress submissions
- **ca_tiers**: Combat achievement tier definitions
- **ca_submissions**: CA tier submissions
- **shop_items**: Available shop items
- **purchases**: User purchase history
- **user_threads**: Individual user thread tracking

### Key Features
- **ACID Compliance**: All transactions are atomic and consistent
- **Audit Trail**: Every point change is logged with reason and admin
- **Performance**: Indexed queries for fast leaderboard updates
- **Scalability**: SQLite handles thousands of users efficiently

## 🔄 Migration from JSON

The system is designed to run alongside the existing JSON-based storage system. Future versions will include migration tools to move existing data to the new database.

## 🚀 Usage Examples

### Awarding Competition Points
```
/award_points 20 "Skill of the Week - 1st place" @user
```

### Awarding Points to Role Members
```
/award_points 10 "Event Participation Bonus" @role
```

### Applying Event Buy-in Penalties
```
/event_penalty "Skill of the Week" -10 @participants_role
/event_penalty "Bingo Night" -5 "username1, username2, username3"
```

### Submitting Collection Log
```
/icpoints @user "Collection Log" 1200 "Reached Dragon tier"
```

### Adding Shop Item
```
/add_shop_item "Custom Role" "Exclusive Discord role" 500 "Roles" 10
```

### Viewing Leaderboard
```
/iceventleaderboard 10
```

## 🔧 Configuration

### Environment Variables
- `GUILD_ID`: Discord guild ID
- `ADMIN_ROLE`: Admin role name
- `EVENT_COORDINATOR_ROLE`: Event coordinator role name

### Database Configuration
- Database file: `leaderboard.db`
- Backup strategy: Manual backups recommended
- Migration: Automatic schema updates

## 📈 Performance

### Optimizations
- **Indexed Queries**: Fast leaderboard and user lookups
- **Connection Pooling**: Efficient database connections
- **Caching**: User data cached in memory
- **Batch Operations**: Efficient bulk updates

### Scalability
- **Current**: Supports 1,000+ users
- **Future**: Can migrate to PostgreSQL for 10,000+ users
- **Storage**: ~1MB per 1,000 users

## 🔒 Security

### Data Protection
- **Input Validation**: All user inputs validated
- **SQL Injection Protection**: Parameterized queries
- **Permission Checks**: Role-based access control
- **Audit Logging**: Complete transaction history

### Admin Controls
- **Point Verification**: All point changes require admin approval
- **Transaction Logging**: Full audit trail of all changes
- **Rollback Capability**: Can reverse incorrect transactions

## 🐛 Troubleshooting

### Common Issues
1. **Database Lock**: Restart bot if database is locked
2. **Permission Errors**: Check user roles and bot permissions
3. **Point Calculation**: Verify competition type and placement
4. **Shop Issues**: Check item availability and user points

### Logging
- All operations logged to `bot.log`
- Database errors logged with full context
- User actions tracked for debugging

## 🔮 Future Enhancements

### Planned Features
- **Individual Threads**: Per-user submission threads
- **Advanced Analytics**: Detailed participation statistics
- **Seasonal Events**: Time-limited competitions
- **Integration APIs**: Connect with external systems
- **Web Dashboard**: Browser-based management interface

### Technical Improvements
- **PostgreSQL Migration**: For larger communities
- **Real-time Updates**: WebSocket-based live updates
- **Mobile Support**: Discord mobile optimization
- **API Endpoints**: REST API for external tools

## 📞 Support

For issues or questions:
1. Check the logs in `bot.log`
2. Verify database integrity
3. Test with minimal data
4. Contact development team

## 📄 License

This module is part of the IC Bingo Bot project and follows the same licensing terms. 