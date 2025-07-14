-- Ironclad Events Leaderboard Database Schema
-- SQLite database for tracking user points, competitions, and achievements

-- Users table - tracks all Discord users
CREATE TABLE users (
    discord_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    display_name TEXT,
    team TEXT,
    total_points INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Competition types table
CREATE TABLE competition_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    max_placements INTEGER DEFAULT 3, -- How many places get points (1st, 2nd, 3rd)
    active BOOLEAN DEFAULT TRUE
);

-- Competition instances table
CREATE TABLE competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_type_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    start_date TIMESTAMP,
    end_date TIMESTAMP,
    status TEXT DEFAULT 'active', -- 'active', 'completed', 'cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (competition_type_id) REFERENCES competition_types(id)
);

-- Competition results table
CREATE TABLE competition_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    placement INTEGER NOT NULL, -- 1, 2, 3, etc.
    points_awarded INTEGER NOT NULL,
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    awarded_by INTEGER, -- Discord ID of admin who awarded
    notes TEXT,
    FOREIGN KEY (competition_id) REFERENCES competitions(id),
    FOREIGN KEY (user_id) REFERENCES users(discord_id),
    FOREIGN KEY (awarded_by) REFERENCES users(discord_id),
    UNIQUE(competition_id, user_id) -- One result per user per competition
);

-- Collection Log tiers table
CREATE TABLE clog_tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    requirement INTEGER NOT NULL, -- Number of items needed
    points INTEGER NOT NULL,
    active BOOLEAN DEFAULT TRUE
);

-- Collection Log submissions table
CREATE TABLE clog_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tier_id INTEGER NOT NULL,
    current_count INTEGER NOT NULL, -- Current collection log count
    points_awarded INTEGER NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_by INTEGER, -- Discord ID of admin who verified
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(discord_id),
    FOREIGN KEY (tier_id) REFERENCES clog_tiers(id),
    FOREIGN KEY (verified_by) REFERENCES users(discord_id)
);

-- Combat Achievement tiers table
CREATE TABLE ca_tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    points INTEGER NOT NULL,
    active BOOLEAN DEFAULT TRUE
);

-- Combat Achievement submissions table
CREATE TABLE ca_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tier_id INTEGER NOT NULL,
    points_awarded INTEGER NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_by INTEGER, -- Discord ID of admin who verified
    notes TEXT,
    FOREIGN KEY (user_id) REFERENCES users(discord_id),
    FOREIGN KEY (tier_id) REFERENCES ca_tiers(id),
    FOREIGN KEY (verified_by) REFERENCES users(discord_id)
);

-- Points transactions table (audit trail)
CREATE TABLE point_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    transaction_type TEXT NOT NULL, -- 'competition', 'clog', 'ca', 'manual', 'shop_purchase'
    reference_id INTEGER, -- ID from the relevant table (competition_result, clog_submission, etc.)
    reason TEXT NOT NULL,
    awarded_by INTEGER, -- Discord ID of admin who awarded
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(discord_id),
    FOREIGN KEY (awarded_by) REFERENCES users(discord_id)
);

-- Shop items table
CREATE TABLE shop_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    cost INTEGER NOT NULL,
    available_quantity INTEGER DEFAULT -1, -- -1 = unlimited
    category TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User purchases table
CREATE TABLE purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    total_cost INTEGER NOT NULL,
    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(discord_id),
    FOREIGN KEY (item_id) REFERENCES shop_items(id)
);

-- Individual threads table
CREATE TABLE user_threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    thread_id INTEGER NOT NULL, -- Discord thread ID
    channel_id INTEGER NOT NULL,
    thread_name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(discord_id)
);

-- ===== BINGO SYSTEM TABLES =====

-- Bingo tiles table - stores tile definitions
CREATE TABLE bingo_tiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tile_index INTEGER NOT NULL, -- 0-99 for 10x10 board
    name TEXT NOT NULL,
    drops_needed INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tile_index)
);

-- Bingo tile drops table - stores required drops for each tile
CREATE TABLE bingo_tile_drops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tile_id INTEGER NOT NULL,
    drop_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
    UNIQUE(tile_id, drop_name)
);

-- Bingo team progress table - tracks team progress on tiles
CREATE TABLE bingo_team_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL,
    tile_id INTEGER NOT NULL,
    total_required INTEGER NOT NULL,
    completed_count INTEGER NOT NULL DEFAULT 0,
    is_complete BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
    UNIQUE(team_name, tile_id)
);

-- Bingo submissions table - stores individual drop submissions
CREATE TABLE bingo_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_name TEXT NOT NULL,
    tile_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL, -- Discord user ID
    drop_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'approved', 'denied', 'hold'
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by INTEGER, -- Discord user ID of approver
    denied_at TIMESTAMP,
    denied_by INTEGER, -- Discord user ID of denier
    denial_reason TEXT,
    hold_at TIMESTAMP,
    hold_by INTEGER, -- Discord user ID who put on hold
    hold_reason TEXT,
    FOREIGN KEY (tile_id) REFERENCES bingo_tiles(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(discord_id),
    FOREIGN KEY (approved_by) REFERENCES users(discord_id),
    FOREIGN KEY (denied_by) REFERENCES users(discord_id),
    FOREIGN KEY (hold_by) REFERENCES users(discord_id)
);

-- Insert default competition types
INSERT INTO competition_types (name, description, max_placements) VALUES
('Skill of the Week', 'Weekly skill-based competitions', 3),
('Clue of the Month', 'Monthly clue scroll competitions', 3),
('Boss of the Week', 'Weekly boss kill competitions', 3),
('General Bingo', 'Team bingo competitions', 2),
('Battleship Bingo', 'Battleship-style bingo competitions', 2),
('Mania', 'Various mini-games and challenges', 3),
('Bounty', 'Target-based competitions', 2);

-- Insert default CLOG tiers
INSERT INTO clog_tiers (name, requirement, points) VALUES
('Guilded', 1400, 200),
('Dragon', 1200, 100),
('Rune', 1100, 90),
('Adamant', 1000, 80),
('Mithril', 900, 50),
('Black', 700, 30),
('Steel', 500, 20),
('Iron', 300, 10),
('Bronze', 100, 5);

-- Insert default CA tiers
INSERT INTO ca_tiers (name, points) VALUES
('Grandmaster', 200),
('Master', 100),
('Elite', 75),
('Hard', 50),
('Medium', 25),
('Easy', 10);

-- Create indexes for better performance
CREATE INDEX idx_competition_results_user_id ON competition_results(user_id);
CREATE INDEX idx_competition_results_competition_id ON competition_results(competition_id);
CREATE INDEX idx_clog_submissions_user_id ON clog_submissions(user_id);
CREATE INDEX idx_ca_submissions_user_id ON ca_submissions(user_id);
CREATE INDEX idx_point_transactions_user_id ON point_transactions(user_id);
CREATE INDEX idx_point_transactions_type ON point_transactions(transaction_type);
CREATE INDEX idx_users_points ON users(total_points DESC);
CREATE INDEX idx_user_threads_user_id ON user_threads(user_id);
CREATE INDEX idx_user_threads_archived ON user_threads(archived);

-- Bingo-specific indexes
CREATE INDEX idx_bingo_tiles_index ON bingo_tiles(tile_index);
CREATE INDEX idx_bingo_team_progress_team ON bingo_team_progress(team_name);
CREATE INDEX idx_bingo_team_progress_tile ON bingo_team_progress(tile_id);
CREATE INDEX idx_bingo_team_progress_complete ON bingo_team_progress(is_complete);
CREATE INDEX idx_bingo_submissions_team ON bingo_submissions(team_name);
CREATE INDEX idx_bingo_submissions_tile ON bingo_submissions(tile_id);
CREATE INDEX idx_bingo_submissions_user ON bingo_submissions(user_id);
CREATE INDEX idx_bingo_submissions_status ON bingo_submissions(status);
CREATE INDEX idx_bingo_submissions_submitted ON bingo_submissions(submitted_at);
CREATE INDEX idx_bingo_tile_drops_tile ON bingo_tile_drops(tile_id); 