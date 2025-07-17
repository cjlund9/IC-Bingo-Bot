import React, { useEffect, useState } from 'react';

function WOMLeaderboard() {
  const [metrics, setMetrics] = useState({ bosses: [], skills: [], clues: [] });
  const [metricType, setMetricType] = useState('boss');
  const [metric, setMetric] = useState('zulrah');
  const [leaderboard, setLeaderboard] = useState([]);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetch('/api/metrics')
      .then(res => res.json())
      .then(setMetrics);
  }, []);

  useEffect(() => {
    fetch(`/api/leaderboard/wom?metric=${metric}&metric_type=${metricType}`)
      .then(res => res.json())
      .then(setLeaderboard);
  }, [metric, metricType]);

  const getOptions = () => {
    if (metricType === 'boss') return metrics.bosses;
    if (metricType === 'skill') return metrics.skills;
    if (metricType === 'clue') return metrics.clues;
    return [];
  };

  const filteredOptions = getOptions().filter(opt =>
    opt.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <h2>WOM API Leaderboard</h2>
      <div style={{ marginBottom: 16 }}>
        <label>Type: </label>
        <select value={metricType} onChange={e => { setMetricType(e.target.value); setMetric(''); setSearch(''); }}>
          <option value="boss">Boss</option>
          <option value="skill">Skill</option>
          <option value="clue">Clue</option>
        </select>
        <input
          style={{ marginLeft: 8 }}
          placeholder="Search..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <select
          value={metric}
          onChange={e => setMetric(e.target.value)}
          style={{ marginLeft: 8 }}
        >
          {filteredOptions.map(opt => (
            <option key={opt} value={opt}>{opt.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</option>
          ))}
        </select>
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Rank</th>
            <th style={{ textAlign: 'left' }}>RSN</th>
            <th style={{ textAlign: 'right' }}>Value</th>
          </tr>
        </thead>
        <tbody>
          {leaderboard.map((entry, i) => (
            <tr key={entry.rsn}>
              <td>{i + 1}</td>
              <td>{entry.rsn}</td>
              <td style={{ textAlign: 'right' }}>{entry.value.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TeamLeaderboard() {
  const [teams, setTeams] = useState([]);

  useEffect(() => {
    fetch('/api/leaderboard/teams')
      .then(res => res.json())
      .then(setTeams);
  }, []);

  return (
    <div>
      <h2>Team Bingo Progress</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Rank</th>
            <th style={{ textAlign: 'left' }}>Team</th>
            <th style={{ textAlign: 'right' }}>Completed</th>
            <th style={{ textAlign: 'right' }}>Total</th>
            <th style={{ textAlign: 'right' }}>Percentage</th>
          </tr>
        </thead>
        <tbody>
          {teams.map((team, i) => (
            <tr key={team.team}>
              <td>{i + 1}</td>
              <td>{team.team}</td>
              <td style={{ textAlign: 'right' }}>{team.completed}</td>
              <td style={{ textAlign: 'right' }}>{team.total}</td>
              <td style={{ textAlign: 'right' }}>{team.percentage}%</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PointsLeaderboard() {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    fetch('/api/leaderboard/points')
      .then(res => res.json())
      .then(setUsers);
  }, []);

  return (
    <div>
      <h2>User Points Leaderboard</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left' }}>Rank</th>
            <th style={{ textAlign: 'left' }}>User</th>
            <th style={{ textAlign: 'left' }}>Team</th>
            <th style={{ textAlign: 'right' }}>Points</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user, i) => (
            <tr key={user.discord_id}>
              <td>{i + 1}</td>
              <td>{user.display_name}</td>
              <td>{user.team || 'None'}</td>
              <td style={{ textAlign: 'right' }}>{user.total_points.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState('wom');

  return (
    <div style={{ maxWidth: 800, margin: '2rem auto', fontFamily: 'sans-serif' }}>
      <h1>Leaderboards</h1>
      
      <div style={{ marginBottom: 20 }}>
        <button 
          style={{ 
            padding: '8px 16px',
            marginRight: 8, 
            backgroundColor: activeTab === 'wom' ? '#7bff' : '#f8f9fa',
            color: activeTab === 'wom' ? 'white' : 'black',
            border: '1px solid #dee2e6',
            cursor: 'pointer'
          }}
          onClick={() => setActiveTab('wom')}
        >
          WOM API
        </button>
        <button 
          style={{ 
            padding: '8px 16px',
            marginRight: 8, 
            backgroundColor: activeTab === 'teams' ? '#7bff' : '#f8f9fa',
            color: activeTab === 'teams' ? 'white' : 'black',
            border: '1px solid #dee2e6',
            cursor: 'pointer'
          }}
          onClick={() => setActiveTab('teams')}
        >
          Team Progress
        </button>
        <button 
          style={{ 
            padding: '8px 16px',
            marginRight: 8, 
            backgroundColor: activeTab === 'points' ? '#7bff' : '#f8f9fa',
            color: activeTab === 'points' ? 'white' : 'black',
            border: '1px solid #dee2e6',
            cursor: 'pointer'
          }}
          onClick={() => setActiveTab('points')}
        >
          User Points
        </button>
      </div>

      {activeTab === 'wom' && <WOMLeaderboard />}
      {activeTab === 'teams' && <TeamLeaderboard />}
      {activeTab === 'points' && <PointsLeaderboard />}
    </div>
  );
}

export default App; 