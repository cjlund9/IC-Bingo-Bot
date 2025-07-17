from flask import Flask, request, jsonify
import requests
import os
import sqlite3
from threading import Lock
import time

app = Flask(__name__)

# Rate limiting for WOM API calls
wom_last_call = 0
wom_lock = Lock()
WOM_COOLDOWN = 5  # seconds

# Example: Replace with your actual user list or fetch from your DB
DISCORD_USERS = [
    {'rsn': 'User1'},
    {'rsn': 'User2'},
    {'rsn': 'User3'},
    # ...
]

BOSSES = [
    "zulrah", "vorkath", "cerberus", "alchemical-hydra", "chambers-of-xeric", "theatre-of-blood", "nex", "general-graardor", "kree'arra", "kril-tsutsaroth"
]
SKILLS = [
    "overall", "attack", "defence", "strength", "hitpoints", "ranged", "prayer", "magic", "cooking", "woodcutting"
]
CLUES = [
    "all", "beginner", "easy", "medium", "hard", "elite", "master"
]

def get_db_conn():
    return sqlite3.connect('leaderboard.db')

@app.route('/api/metrics')
def metrics():
    return jsonify({
        'bosses': BOSSES,
        'skills': SKILLS,
        'clues': CLUES
    })

@app.route('/api/leaderboard/wom')
def wom_leaderboard():
    metric = request.args.get('metric', 'zulrah')
    metric_type = request.args.get('metric_type', 'boss')
    leaderboard = []
    for user in DISCORD_USERS:
        rsn = user['rsn']
        value = get_wom_metric(rsn, metric_type, metric)
        leaderboard.append({'rsn': rsn, 'value': value})
    leaderboard.sort(key=lambda x: x['value'], reverse=True)
    return jsonify(leaderboard)

@app.route('/api/leaderboard/teams')
def team_leaderboard():
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # Get team progress for all teams
        teams = ['moles', 'obor']  # Add your actual team names
        team_stats = []
        
        for team in teams:
            cursor.execute('''
                SELECT COUNT(*) as total_tiles,
                       SUM(CASE WHEN is_complete = 1 THEN 1 ELSE 0 END) as completed_tiles
                FROM bingo_team_progress 
                WHERE team_name = ?
            ''', (team,))
            
            result = cursor.fetchone()
            if result:
                total, completed = result
                completion_percentage = (completed / total *100 if total > 0 else0)
                team_stats.append({
                    'team': team.capitalize(),
                    'completed': completed,
                    'total': total,
                    'percentage': round(completion_percentage, 1)
                })
        
        conn.close()
        team_stats.sort(key=lambda x: x['percentage'], reverse=True)
        return jsonify(team_stats)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/leaderboard/points')
def points_leaderboard():
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT discord_id, username, display_name, team, total_points, last_active
            FROM users 
            ORDER BY total_points DESC, last_active DESC
            LIMIT 50
        ''')
        
        leaderboard = []
        for row in cursor.fetchall():
            leaderboard.append({
                'discord_id': row[0],
                'username': row[1],
                'display_name': row[2] or row[1],
                'team': row[3],
                'total_points': row[4],
                'last_active': row[5]
            })
        
        conn.close()
        return jsonify(leaderboard)
        
    except Exception as e:
        return jsonify({'error': str(e)}),500

def get_wom_metric(rsn, metric_type, metric):
    global wom_last_call
    # Rate limiting: ensure at least 5 seconds between calls
    with wom_lock:
        current_time = time.time()
        time_since_last = current_time - wom_last_call
        if time_since_last < WOM_COOLDOWN:
            sleep_time = WOM_COOLDOWN - time_since_last
            time.sleep(sleep_time)
        wom_last_call = time.time()
    url = f"https://api.wiseoldman.net/v2/players/{rsn}/hiscores"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if metric_type == "boss":
                for b in data.get("bosses", []):
                    if b["metric"].lower() == metric.lower():
                        return b["value"]
            elif metric_type == "skill":
                for s in data.get("skills", []):
                    if s["metric"].lower() == metric.lower():
                        return s["experience"]
            elif metric_type == "clue":
                for c in data.get("clues", []):
                    if c["metric"].lower() == metric.lower():
                        return c["value"]
        return 0
    except Exception:
        return 0

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000) 