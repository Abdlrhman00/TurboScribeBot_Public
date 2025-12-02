const express = require('express');
const cors = require('cors');
require('dotenv').config();

const jobRoutes = require('./routes/jobs');
const fileRoutes = require('./routes/files.js');
const { apiKeyAuth } = require('./middlewares/auth');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());

app.use(apiKeyAuth); 

// Routes
app.use('/api/jobs', jobRoutes);
app.use('/api/files', fileRoutes);

// Health check
app.get('/health', (req, res) => {
  res.json({ 
    status: 'OK', 
    service: 'TurboScribeBot API',
    timestamp: new Date().toISOString() 
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Endpoint not found',
    availableEndpoints: {
      'GET /health': 'Service health check',
      'POST /api/jobs': 'Create new transcription job',
      'GET /api/jobs': 'List all jobs',
      'GET /api/jobs/:jobId': 'Get job status',
      'GET /api/jobs/:jobId/logs': 'Get job logs',
      'GET /api/jobs/:jobId/report': 'Get job report',
      'GET /api/jobs/:jobId/outputs': 'Get all outputs',
      'DELETE /api/jobs/:jobId': 'Cancel job',
      'POST /api/files/copy': 'Copy files between accounts'
    }
  });
});

// Error handler
app.use((error, req, res, next) => {
  console.error('Server Error:', error);
  res.status(500).json({
    error: 'Internal server error',
    details: process.env.NODE_ENV === 'development' ? error.message : 'Something went wrong'
  });
});

app.listen(PORT, () => {
  console.log(`🚀 TurboScribe API running on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
});