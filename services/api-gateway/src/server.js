const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const redis = require('redis');
const jwt = require('jsonwebtoken');
const winston = require('winston');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 8000;

// Logger configuration
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'logs/gateway.log' })
  ]
});

// Redis client for rate limiting and caching
const redisClient = redis.createClient({
  url: process.env.REDIS_URL || 'redis://localhost:6379'
});

redisClient.on('error', (err) => {
  logger.error('Redis Client Error', err);
});

redisClient.connect();

// Middleware
app.use(helmet());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true
}));

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // limit each IP to 1000 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
  store: {
    // Custom Redis store for rate limiting
    async increment(key) {
      const current = await redisClient.incr(key);
      if (current === 1) {
        await redisClient.expire(key, 900); // 15 minutes
      }
      return { totalHits: current, resetTime: new Date(Date.now() + 900000) };
    },
    async decrement(key) {
      return await redisClient.decr(key);
    },
    async resetKey(key) {
      return await redisClient.del(key);
    }
  }
});

app.use(limiter);

// Request logging
app.use((req, res, next) => {
  logger.info('Incoming request', {
    method: req.method,
    url: req.url,
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });
  next();
});

// Authentication middleware
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  jwt.verify(token, process.env.JWT_SECRET || 'default-secret', (err, user) => {
    if (err) {
      return res.status(403).json({ error: 'Invalid or expired token' });
    }
    req.user = user;
    next();
  });
};

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    services: {
      redis: redisClient.isReady ? 'connected' : 'disconnected'
    }
  });
});

// Service routing configuration
const services = {
  ats: {
    target: process.env.ATS_SERVICE_URL || 'http://ats-service:8000',
    pathRewrite: { '^/api/v1/ats': '' }
  },
  resume: {
    target: process.env.RESUME_SERVICE_URL || 'http://resume-service:8000',
    pathRewrite: { '^/api/v1/resume': '' }
  },
  matching: {
    target: process.env.MATCHING_SERVICE_URL || 'http://matching-service:8000',
    pathRewrite: { '^/api/v1/matching': '' }
  },
  testing: {
    target: process.env.TESTING_SERVICE_URL || 'http://testing-service:3000',
    pathRewrite: { '^/api/v1/testing': '' }
  },
  notification: {
    target: process.env.NOTIFICATION_SERVICE_URL || 'http://notification-service:8000',
    pathRewrite: { '^/api/v1/notification': '' }
  }
};

// Create proxy middleware for each service
Object.entries(services).forEach(([serviceName, config]) => {
  const proxyOptions = {
    target: config.target,
    changeOrigin: true,
    pathRewrite: config.pathRewrite,
    onError: (err, req, res) => {
      logger.error(`Proxy error for ${serviceName}`, {
        error: err.message,
        target: config.target,
        path: req.path
      });
      res.status(502).json({
        error: 'Service temporarily unavailable',
        service: serviceName
      });
    },
    onProxyReq: (proxyReq, req, res) => {
      // Add user context to proxied requests
      if (req.user) {
        proxyReq.setHeader('X-User-ID', req.user.id);
        proxyReq.setHeader('X-User-Role', req.user.role);
      }
    }
  };

  // Apply authentication to protected routes
  if (serviceName !== 'auth') {
    app.use(`/api/v1/${serviceName}`, authenticateToken, createProxyMiddleware(proxyOptions));
  } else {
    app.use(`/api/v1/${serviceName}`, createProxyMiddleware(proxyOptions));
  }
});

// Public routes (no authentication required)
app.use('/api/v1/auth', createProxyMiddleware({
  target: services.ats.target,
  changeOrigin: true,
  pathRewrite: { '^/api/v1/auth': '/auth' }
}));

// API documentation route
app.get('/api/v1/docs', (req, res) => {
  res.json({
    title: 'Recruitment Platform API Gateway',
    version: '1.0.0',
    services: Object.keys(services),
    endpoints: {
      '/api/v1/ats': 'Applicant Tracking System',
      '/api/v1/resume': 'Resume Parsing Service',
      '/api/v1/matching': 'Candidate Matching Service',
      '/api/v1/testing': 'Online Testing Platform',
      '/api/v1/notification': 'Notification Service'
    }
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error', {
    error: err.message,
    stack: err.stack,
    path: req.path,
    method: req.method
  });

  res.status(500).json({
    error: 'Internal server error',
    requestId: req.id
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({
    error: 'Route not found',
    path: req.originalUrl
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully');
  await redisClient.quit();
  process.exit(0);
});

process.on('SIGINT', async () => {
  logger.info('SIGINT received, shutting down gracefully');
  await redisClient.quit();
  process.exit(0);
});

app.listen(PORT, () => {
  logger.info(`API Gateway running on port ${PORT}`);
});