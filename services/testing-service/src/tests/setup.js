// Test setup file
require('dotenv').config();

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.MONGODB_TEST_URL = process.env.MONGODB_TEST_URL || 'mongodb://localhost:27017/recruitment_test';
process.env.REDIS_HOST = process.env.REDIS_HOST || 'localhost';
process.env.REDIS_PORT = process.env.REDIS_PORT || '6379';

// Global test timeout
jest.setTimeout(30000);