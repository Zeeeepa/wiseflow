const express = require('express');
const path = require('path');
const bodyParser = require('body-parser');

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Serve static files
app.use('/static', express.static(path.join(__dirname, 'dashboard/static')));

// API routes
app.get('/api/v1/data-mining/tasks', (req, res) => {
  // Mock data for demonstration
  const tasks = [
    { id: 1, name: 'GitHub Research', source: 'github', status: 'active', progress: 75 },
    { id: 2, name: 'ArXiv Papers Analysis', source: 'arxiv', status: 'paused', progress: 45 },
    { id: 3, name: 'YouTube Tech Trends', source: 'youtube', status: 'completed', progress: 100 },
    { id: 4, name: 'Web Research on AI', source: 'web', status: 'active', progress: 30 }
  ];
  
  res.json({ success: true, data: tasks });
});

app.get('/api/v1/data-mining/tasks/:id/findings', (req, res) => {
  // Mock data for demonstration
  const findings = [
    {
      id: 1,
      title: 'Tech Companies Expanding in Texas',
      summary: 'Multiple tech companies including Apple, Google, and Microsoft are expanding operations in Texas.',
      source: 'web',
      date: '2023-05-15',
      relevance: 0.92,
      tags: ['tech', 'expansion', 'jobs']
    },
    {
      id: 2,
      title: 'Apple\'s New Campus in Austin',
      summary: 'Apple is building a new campus in Austin that will create 5,000 jobs initially.',
      source: 'github',
      date: '2023-05-14',
      relevance: 0.88,
      tags: ['apple', 'campus', 'jobs']
    },
    {
      id: 3,
      title: 'Job Growth in Tech Sector',
      summary: 'The tech sector continues to show strong job growth despite economic concerns.',
      source: 'arxiv',
      date: '2023-05-12',
      relevance: 0.75,
      tags: ['jobs', 'economy', 'growth']
    },
    {
      id: 4,
      title: 'Tim Cook Announces Expansion Plans',
      summary: 'Apple CEO Tim Cook announced expansion plans for the company in multiple states.',
      source: 'youtube',
      date: '2023-05-10',
      relevance: 0.95,
      tags: ['apple', 'expansion', 'tim cook']
    }
  ];
  
  res.json({ success: true, data: findings });
});

// Route for dashboard
app.get(['/', '/dashboard'], (req, res) => {
  res.sendFile(path.join(__dirname, 'dashboard/templates/dashboard.html'));
});

// Routes for other pages
app.get('/data-mining', (req, res) => {
  res.sendFile(path.join(__dirname, 'dashboard/templates/data_mining_dashboard.html'));
});

app.get('/templates', (req, res) => {
  res.sendFile(path.join(__dirname, 'dashboard/templates/templates_management.html'));
});

app.get('/database', (req, res) => {
  res.sendFile(path.join(__dirname, 'dashboard/templates/database_management.html'));
});

app.get('/visualization', (req, res) => {
  res.sendFile(path.join(__dirname, 'dashboard/templates/visualization.html'));
});

app.get('/settings', (req, res) => {
  res.sendFile(path.join(__dirname, 'dashboard/templates/settings.html'));
});

// Catch-all route for SPA
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dashboard/templates/dashboard.html'));
});

// Start server
app.listen(port, () => {
  console.log(`Wiseflow Dashboard server running on port ${port}`);
  console.log(`Open http://localhost:${port} in your browser`);
});

