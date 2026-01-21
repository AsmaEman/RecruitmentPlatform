/**
 * Session management service with auto-save functionality
 * Requirements: 4.5, 4.6
 */

const mongoose = require('mongoose');
const redis = require('redis');
const { v4: uuidv4 } = require('uuid');

class SessionManager {
  constructor() {
    this.redisClient = null;
    this.logger = require('../utils/logger');
    this.autoSaveInterval = 30000; // 30 seconds
    this.activeSessions = new Map();
  }

  /**
   * Initialize session manager
   */
  async initialize() {
    try {
      // Initialize Redis client
      this.redisClient = redis.createClient({
        host: process.env.REDIS_HOST || 'localhost',
        port: process.env.REDIS_PORT || 6379,
        password: process.env.REDIS_PASSWORD
      });

      await this.redisClient.connect();
      this.logger.info('Session manager initialized');

      return { success: true };
    } catch (error) {
      this.logger.error(`Session manager initialization failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Create a new test session
   */
  async createSession(candidateId, testId, options = {}) {
    try {
      const sessionId = uuidv4();
      const now = new Date();

      const session = {
        sessionId,
        candidateId,
        testId,
        status: 'active',
        startTime: now,
        endTime: null,
        timeLimit: options.timeLimit || 3600000, // 1 hour default
        autoSaveEnabled: options.autoSaveEnabled !== false,
        currentQuestionIndex: 0,
        answers: {},
        codeSubmissions: {},
        violations: [],
        metadata: {
          userAgent: options.userAgent,
          ipAddress: options.ipAddress,
          browserFingerprint: options.browserFingerprint
        },
        lastActivity: now,
        lastAutoSave: now
      };

      // Save to MongoDB
      const TestSession = require('../models/TestSession');
      const sessionDoc = new TestSession(session);
      await sessionDoc.save();

      // Cache in Redis for fast access
      await this.redisClient.setEx(
        `session:${sessionId}`,
        3600, // 1 hour TTL
        JSON.stringify(session)
      );

      // Start auto-save if enabled
      if (session.autoSaveEnabled) {
        this.startAutoSave(sessionId);
      }

      this.logger.info(`Session created: ${sessionId} for candidate: ${candidateId}`);

      return {
        success: true,
        sessionId,
        session: {
          sessionId: session.sessionId,
          status: session.status,
          startTime: session.startTime,
          timeLimit: session.timeLimit,
          currentQuestionIndex: session.currentQuestionIndex
        }
      };

    } catch (error) {
      this.logger.error(`Session creation failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Get session by ID
   */
  async getSession(sessionId) {
    try {
      // Try Redis first
      const cached = await this.redisClient.get(`session:${sessionId}`);
      if (cached) {
        return { success: true, session: JSON.parse(cached) };
      }

      // Fall back to MongoDB
      const TestSession = require('../models/TestSession');
      const session = await TestSession.findOne({ sessionId });

      if (!session) {
        return { success: false, error: 'Session not found' };
      }

      // Update Redis cache
      await this.redisClient.setEx(
        `session:${sessionId}`,
        3600,
        JSON.stringify(session.toObject())
      );

      return { success: true, session: session.toObject() };

    } catch (error) {
      this.logger.error(`Get session failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Update session data
   */
  async updateSession(sessionId, updates) {
    try {
      const sessionResult = await this.getSession(sessionId);
      if (!sessionResult.success) {
        return sessionResult;
      }

      const session = sessionResult.session;
      const now = new Date();

      // Apply updates
      Object.assign(session, updates, {
        lastActivity: now
      });

      // Update MongoDB
      const TestSession = require('../models/TestSession');
      await TestSession.updateOne(
        { sessionId },
        { $set: session }
      );

      // Update Redis cache
      await this.redisClient.setEx(
        `session:${sessionId}`,
        3600,
        JSON.stringify(session)
      );

      return { success: true, session };

    } catch (error) {
      this.logger.error(`Session update failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Auto-save session progress
   */
  async autoSave(sessionId, data) {
    try {
      const now = new Date();

      const updates = {
        ...data,
        lastAutoSave: now,
        lastActivity: now
      };

      const result = await this.updateSession(sessionId, updates);

      if (result.success) {
        this.logger.debug(`Auto-save completed for session: ${sessionId}`);
      }

      return result;

    } catch (error) {
      this.logger.error(`Auto-save failed for session ${sessionId}: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Start auto-save for a session
   */
  startAutoSave(sessionId) {
    if (this.activeSessions.has(sessionId)) {
      return; // Already started
    }

    const intervalId = setInterval(async () => {
      try {
        const sessionResult = await this.getSession(sessionId);
        if (!sessionResult.success || sessionResult.session.status !== 'active') {
          this.stopAutoSave(sessionId);
          return;
        }

        // Check if session needs auto-save (has been modified)
        const session = sessionResult.session;
        const timeSinceLastSave = Date.now() - new Date(session.lastAutoSave).getTime();

        if (timeSinceLastSave >= this.autoSaveInterval) {
          await this.autoSave(sessionId, {});
        }

      } catch (error) {
        this.logger.error(`Auto-save interval error for session ${sessionId}: ${error.message}`);
      }
    }, this.autoSaveInterval);

    this.activeSessions.set(sessionId, intervalId);
    this.logger.debug(`Auto-save started for session: ${sessionId}`);
  }

  /**
   * Stop auto-save for a session
   */
  stopAutoSave(sessionId) {
    const intervalId = this.activeSessions.get(sessionId);
    if (intervalId) {
      clearInterval(intervalId);
      this.activeSessions.delete(sessionId);
      this.logger.debug(`Auto-save stopped for session: ${sessionId}`);
    }
  }

  /**
   * Submit answer for a question
   */
  async submitAnswer(sessionId, questionId, answer) {
    try {
      const sessionResult = await this.getSession(sessionId);
      if (!sessionResult.success) {
        return sessionResult;
      }

      const session = sessionResult.session;

      // Update answers
      session.answers[questionId] = {
        answer,
        timestamp: new Date(),
        questionId
      };

      const result = await this.updateSession(sessionId, {
        answers: session.answers
      });

      return result;

    } catch (error) {
      this.logger.error(`Submit answer failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Submit code for a coding question
   */
  async submitCode(sessionId, questionId, code, language) {
    try {
      const sessionResult = await this.getSession(sessionId);
      if (!sessionResult.success) {
        return sessionResult;
      }

      const session = sessionResult.session;

      // Update code submissions
      session.codeSubmissions[questionId] = {
        code,
        language,
        timestamp: new Date(),
        questionId
      };

      const result = await this.updateSession(sessionId, {
        codeSubmissions: session.codeSubmissions
      });

      return result;

    } catch (error) {
      this.logger.error(`Submit code failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Record a violation
   */
  async recordViolation(sessionId, violation) {
    try {
      const sessionResult = await this.getSession(sessionId);
      if (!sessionResult.success) {
        return sessionResult;
      }

      const session = sessionResult.session;

      // Add violation
      session.violations.push({
        ...violation,
        timestamp: new Date()
      });

      const result = await this.updateSession(sessionId, {
        violations: session.violations
      });

      return result;

    } catch (error) {
      this.logger.error(`Record violation failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * End session
   */
  async endSession(sessionId, reason = 'completed') {
    try {
      const now = new Date();

      const result = await this.updateSession(sessionId, {
        status: 'completed',
        endTime: now,
        endReason: reason
      });

      // Stop auto-save
      this.stopAutoSave(sessionId);

      // Remove from Redis cache after delay
      setTimeout(async () => {
        try {
          await this.redisClient.del(`session:${sessionId}`);
        } catch (error) {
          this.logger.warn(`Failed to remove session from cache: ${error.message}`);
        }
      }, 60000); // 1 minute delay

      this.logger.info(`Session ended: ${sessionId}, reason: ${reason}`);

      return result;

    } catch (error) {
      this.logger.error(`End session failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Resume session (for recovery)
   */
  async resumeSession(sessionId) {
    try {
      const sessionResult = await this.getSession(sessionId);
      if (!sessionResult.success) {
        return sessionResult;
      }

      const session = sessionResult.session;

      // Check if session is still valid
      if (session.status !== 'active') {
        return { success: false, error: 'Session is not active' };
      }

      // Check if session has expired
      const now = new Date();
      const sessionEnd = new Date(session.startTime.getTime() + session.timeLimit);

      if (now > sessionEnd) {
        await this.endSession(sessionId, 'expired');
        return { success: false, error: 'Session has expired' };
      }

      // Restart auto-save if enabled
      if (session.autoSaveEnabled) {
        this.startAutoSave(sessionId);
      }

      return {
        success: true,
        session: {
          sessionId: session.sessionId,
          status: session.status,
          startTime: session.startTime,
          timeLimit: session.timeLimit,
          currentQuestionIndex: session.currentQuestionIndex,
          answers: session.answers,
          codeSubmissions: session.codeSubmissions,
          timeRemaining: sessionEnd.getTime() - now.getTime()
        }
      };

    } catch (error) {
      this.logger.error(`Resume session failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Get session statistics
   */
  async getSessionStats(sessionId) {
    try {
      const sessionResult = await this.getSession(sessionId);
      if (!sessionResult.success) {
        return sessionResult;
      }

      const session = sessionResult.session;
      const now = new Date();
      const startTime = new Date(session.startTime);

      const stats = {
        sessionId,
        duration: now.getTime() - startTime.getTime(),
        questionsAnswered: Object.keys(session.answers).length,
        codeSubmissions: Object.keys(session.codeSubmissions).length,
        violations: session.violations.length,
        lastActivity: session.lastActivity,
        lastAutoSave: session.lastAutoSave,
        status: session.status
      };

      return { success: true, stats };

    } catch (error) {
      this.logger.error(`Get session stats failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Cleanup expired sessions
   */
  async cleanupExpiredSessions() {
    try {
      const now = new Date();
      const TestSession = require('../models/TestSession');

      // Find expired active sessions
      const expiredSessions = await TestSession.find({
        status: 'active',
        $expr: {
          $lt: [
            { $add: ['$startTime', '$timeLimit'] },
            now
          ]
        }
      });

      let cleanedCount = 0;

      for (const session of expiredSessions) {
        await this.endSession(session.sessionId, 'expired');
        cleanedCount++;
      }

      this.logger.info(`Cleaned up ${cleanedCount} expired sessions`);

      return { success: true, cleanedCount };

    } catch (error) {
      this.logger.error(`Cleanup expired sessions failed: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Shutdown session manager
   */
  async shutdown() {
    try {
      // Stop all auto-save intervals
      for (const [sessionId, intervalId] of this.activeSessions) {
        clearInterval(intervalId);
      }
      this.activeSessions.clear();

      // Close Redis connection
      if (this.redisClient) {
        await this.redisClient.quit();
      }

      this.logger.info('Session manager shutdown complete');

    } catch (error) {
      this.logger.error(`Session manager shutdown error: ${error.message}`);
    }
  }
}

module.exports = SessionManager;