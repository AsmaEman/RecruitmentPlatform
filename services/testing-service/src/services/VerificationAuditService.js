/**
 * Verification audit logging service
 * Requirements: 6.6
 */

const crypto = require('crypto');

class VerificationAuditService {
  constructor() {
    this.logger = require('../utils/logger');
    this.auditLogs = new Map(); // In production, use persistent storage
    this.auditConfig = {
      retentionDays: 365, // Keep audit logs for 1 year
      maxEntriesPerSession: 1000
    };
  }

  /**
   * Log verification attempt
   */
  logVerificationAttempt(sessionId, candidateId, factorType, attempt) {
    try {
      const auditEntry = {
        id: crypto.randomUUID(),
        sessionId,
        candidateId,
        factorType,
        attemptType: attempt.type, // 'initiate', 'verify', 'fail', 'success'
        timestamp: new Date(),
        details: {
          success: attempt.success,
          error: attempt.error,
          confidence: attempt.confidence,
          metadata: attempt.metadata || {}
        },
        ipAddress: attempt.ipAddress,
        userAgent: attempt.userAgent,
        fingerprint: this.generateFingerprint(attempt)
      };

      // Store audit entry
      if (!this.auditLogs.has(sessionId)) {
        this.auditLogs.set(sessionId, []);
      }

      const sessionLogs = this.auditLogs.get(sessionId);
      sessionLogs.push(auditEntry);

      // Enforce max entries per session
      if (sessionLogs.length > this.auditConfig.maxEntriesPerSession) {
        sessionLogs.shift(); // Remove oldest entry
      }

      this.logger.info(`Verification audit logged: ${factorType} ${attempt.type} for candidate ${candidateId}`);

      return {
        success: true,
        auditId: auditEntry.id,
        timestamp: auditEntry.timestamp
      };

    } catch (error) {
      this.logger.error(`Audit logging error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Log MFA session initialization
   */
  logSessionInitialization(sessionId, candidateId, requiredFactors, metadata = {}) {
    return this.logVerificationAttempt(sessionId, candidateId, 'session', {
      type: 'initiate',
      success: true,
      metadata: {
        requiredFactors,
        ...metadata
      },
      ipAddress: metadata.ipAddress,
      userAgent: metadata.userAgent
    });
  }

  /**
   * Log OTP generation
   */
  logOTPGeneration(sessionId, candidateId, factorType, metadata = {}) {
    return this.logVerificationAttempt(sessionId, candidateId, factorType, {
      type: 'otp_generate',
      success: true,
      metadata: {
        otpLength: metadata.otpLength || 6,
        expiryMinutes: metadata.expiryMinutes || 5,
        ...metadata
      },
      ipAddress: metadata.ipAddress,
      userAgent: metadata.userAgent
    });
  }

  /**
   * Log OTP verification attempt
   */
  logOTPVerification(sessionId, candidateId, factorType, success, error = null, metadata = {}) {
    return this.logVerificationAttempt(sessionId, candidateId, factorType, {
      type: 'otp_verify',
      success,
      error,
      metadata: {
        attemptNumber: metadata.attemptNumber,
        remainingAttempts: metadata.remainingAttempts,
        ...metadata
      },
      ipAddress: metadata.ipAddress,
      userAgent: metadata.userAgent
    });
  }

  /**
   * Log photo ID upload and verification
   */
  logPhotoIDVerification(sessionId, candidateId, success, confidence = null, error = null, metadata = {}) {
    return this.logVerificationAttempt(sessionId, candidateId, 'photoId', {
      type: 'photo_verify',
      success,
      error,
      confidence,
      metadata: {
        fileSize: metadata.fileSize,
        fileType: metadata.fileType,
        processingTime: metadata.processingTime,
        ...metadata
      },
      ipAddress: metadata.ipAddress,
      userAgent: metadata.userAgent
    });
  }

  /**
   * Log biometric verification
   */
  logBiometricVerification(sessionId, candidateId, success, confidence = null, error = null, metadata = {}) {
    return this.logVerificationAttempt(sessionId, candidateId, 'biometric', {
      type: 'biometric_verify',
      success,
      error,
      confidence,
      metadata: {
        biometricType: metadata.biometricType || 'facial',
        templateMatch: metadata.templateMatch,
        threshold: metadata.threshold,
        ...metadata
      },
      ipAddress: metadata.ipAddress,
      userAgent: metadata.userAgent
    });
  }

  /**
   * Log MFA completion
   */
  logMFACompletion(sessionId, candidateId, success, verifiedFactors = [], metadata = {}) {
    return this.logVerificationAttempt(sessionId, candidateId, 'session', {
      type: 'complete',
      success,
      metadata: {
        verifiedFactors,
        completionTime: metadata.completionTime,
        totalAttempts: metadata.totalAttempts,
        ...metadata
      },
      ipAddress: metadata.ipAddress,
      userAgent: metadata.userAgent
    });
  }

  /**
   * Log token generation
   */
  logTokenGeneration(sessionId, candidateId, success, error = null, metadata = {}) {
    return this.logVerificationAttempt(sessionId, candidateId, 'token', {
      type: 'generate',
      success,
      error,
      metadata: {
        tokenExpiry: metadata.tokenExpiry,
        verifiedFactors: metadata.verifiedFactors,
        ...metadata
      },
      ipAddress: metadata.ipAddress,
      userAgent: metadata.userAgent
    });
  }

  /**
   * Get audit trail for a session
   */
  getSessionAuditTrail(sessionId) {
    try {
      const sessionLogs = this.auditLogs.get(sessionId) || [];

      return {
        success: true,
        sessionId,
        totalEntries: sessionLogs.length,
        entries: sessionLogs.map(entry => ({
          id: entry.id,
          factorType: entry.factorType,
          attemptType: entry.attemptType,
          timestamp: entry.timestamp,
          success: entry.details.success,
          confidence: entry.details.confidence,
          error: entry.details.error,
          metadata: { ...entry.details.metadata } // Create a copy to prevent mutation
        }))
      };

    } catch (error) {
      this.logger.error(`Audit trail retrieval error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Get audit trail for a candidate
   */
  getCandidateAuditTrail(candidateId, options = {}) {
    try {
      const allEntries = [];

      for (const [sessionId, sessionLogs] of this.auditLogs.entries()) {
        const candidateEntries = sessionLogs.filter(entry => entry.candidateId === candidateId);
        allEntries.push(...candidateEntries.map(entry => ({ ...entry, sessionId })));
      }

      // Sort by timestamp
      allEntries.sort((a, b) => b.timestamp - a.timestamp);

      // Apply filters
      let filteredEntries = allEntries;

      if (options.factorType) {
        filteredEntries = filteredEntries.filter(entry => entry.factorType === options.factorType);
      }

      if (options.attemptType) {
        filteredEntries = filteredEntries.filter(entry => entry.attemptType === options.attemptType);
      }

      if (options.startDate) {
        filteredEntries = filteredEntries.filter(entry => entry.timestamp >= options.startDate);
      }

      if (options.endDate) {
        filteredEntries = filteredEntries.filter(entry => entry.timestamp <= options.endDate);
      }

      // Apply pagination
      const limit = options.limit || 100;
      const offset = options.offset || 0;
      const paginatedEntries = filteredEntries.slice(offset, offset + limit);

      return {
        success: true,
        candidateId,
        totalEntries: filteredEntries.length,
        returnedEntries: paginatedEntries.length,
        entries: paginatedEntries.map(entry => ({
          id: entry.id,
          sessionId: entry.sessionId,
          factorType: entry.factorType,
          attemptType: entry.attemptType,
          timestamp: entry.timestamp,
          success: entry.details.success,
          confidence: entry.details.confidence,
          error: entry.details.error,
          metadata: entry.details.metadata,
          ipAddress: entry.ipAddress,
          fingerprint: entry.fingerprint
        }))
      };

    } catch (error) {
      this.logger.error(`Candidate audit trail retrieval error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Get verification statistics
   */
  getVerificationStatistics(options = {}) {
    try {
      const stats = {
        totalSessions: 0,
        completedSessions: 0,
        failedSessions: 0,
        factorStats: {
          email: { attempts: 0, successes: 0, failures: 0 },
          sms: { attempts: 0, successes: 0, failures: 0 },
          photoId: { attempts: 0, successes: 0, failures: 0 },
          biometric: { attempts: 0, successes: 0, failures: 0 }
        },
        averageCompletionTime: 0,
        securityIncidents: 0
      };

      const sessionCompletionTimes = [];
      const uniqueSessions = new Set();

      for (const [sessionId, sessionLogs] of this.auditLogs.entries()) {
        uniqueSessions.add(sessionId);

        // Filter by date range if specified
        let filteredLogs = sessionLogs;
        if (options.startDate || options.endDate) {
          filteredLogs = sessionLogs.filter(entry => {
            if (options.startDate && entry.timestamp < options.startDate) return false;
            if (options.endDate && entry.timestamp > options.endDate) return false;
            return true;
          });
        }

        if (filteredLogs.length === 0) continue;

        // Check session completion
        const sessionStart = filteredLogs.find(entry => entry.attemptType === 'initiate');
        const sessionComplete = filteredLogs.find(entry => entry.attemptType === 'complete');

        if (sessionComplete) {
          if (sessionComplete.details.success) {
            stats.completedSessions++;
            if (sessionStart) {
              const completionTime = sessionComplete.timestamp - sessionStart.timestamp;
              sessionCompletionTimes.push(completionTime);
            }
          } else {
            stats.failedSessions++;
          }
        } else if (sessionStart) {
          // Session was started but never completed - check if it has failed verification attempts
          const hasFailedAttempts = filteredLogs.some(entry =>
            entry.attemptType.includes('verify') && !entry.details.success
          );

          if (hasFailedAttempts) {
            stats.failedSessions++;
          }
        }

        // Factor statistics
        for (const entry of filteredLogs) {
          if (stats.factorStats[entry.factorType]) {
            if (entry.attemptType.includes('verify')) {
              stats.factorStats[entry.factorType].attempts++;
              if (entry.details.success) {
                stats.factorStats[entry.factorType].successes++;
              } else {
                stats.factorStats[entry.factorType].failures++;
              }
            }
          }

          // Security incidents (multiple failed attempts, suspicious patterns)
          if (!entry.details.success && entry.details.error) {
            if (entry.details.error.includes('exceeded') || entry.details.error.includes('suspicious')) {
              stats.securityIncidents++;
            }
          }
        }
      }

      stats.totalSessions = uniqueSessions.size;

      // Calculate average completion time
      if (sessionCompletionTimes.length > 0) {
        const totalTime = sessionCompletionTimes.reduce((sum, time) => sum + time, 0);
        stats.averageCompletionTime = Math.round(totalTime / sessionCompletionTimes.length / 1000); // in seconds
      }

      // Calculate success rates
      for (const factor in stats.factorStats) {
        const factorStats = stats.factorStats[factor];
        factorStats.successRate = factorStats.attempts > 0
          ? Math.round((factorStats.successes / factorStats.attempts) * 100)
          : 0;
      }

      stats.overallSuccessRate = stats.totalSessions > 0
        ? Math.round((stats.completedSessions / stats.totalSessions) * 100)
        : 0;

      return {
        success: true,
        statistics: stats,
        generatedAt: new Date()
      };

    } catch (error) {
      this.logger.error(`Statistics generation error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Export audit logs
   */
  exportAuditLogs(format = 'json', options = {}) {
    try {
      const allEntries = [];

      for (const [sessionId, sessionLogs] of this.auditLogs.entries()) {
        for (const entry of sessionLogs) {
          // Apply filters
          if (options.candidateId && entry.candidateId !== options.candidateId) continue;
          if (options.factorType && entry.factorType !== options.factorType) continue;
          if (options.startDate && entry.timestamp < options.startDate) continue;
          if (options.endDate && entry.timestamp > options.endDate) continue;

          allEntries.push({
            sessionId,
            ...entry
          });
        }
      }

      // Sort by timestamp
      allEntries.sort((a, b) => a.timestamp - b.timestamp);

      let exportData;
      switch (format.toLowerCase()) {
        case 'csv':
          exportData = this.convertToCSV(allEntries);
          break;
        case 'json':
        default:
          exportData = JSON.stringify(allEntries, null, 2);
          break;
      }

      return {
        success: true,
        format,
        totalRecords: allEntries.length,
        data: exportData,
        exportedAt: new Date()
      };

    } catch (error) {
      this.logger.error(`Audit export error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Clean up expired audit logs
   */
  cleanupExpiredLogs() {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - this.auditConfig.retentionDays);

      let cleanedCount = 0;

      for (const [sessionId, sessionLogs] of this.auditLogs.entries()) {
        const filteredLogs = sessionLogs.filter(entry => entry.timestamp > cutoffDate);

        if (filteredLogs.length !== sessionLogs.length) {
          cleanedCount += sessionLogs.length - filteredLogs.length;

          if (filteredLogs.length === 0) {
            this.auditLogs.delete(sessionId);
          } else {
            this.auditLogs.set(sessionId, filteredLogs);
          }
        }
      }

      if (cleanedCount > 0) {
        this.logger.info(`Cleaned up ${cleanedCount} expired audit log entries`);
      }

      return {
        success: true,
        cleanedCount,
        cutoffDate
      };

    } catch (error) {
      this.logger.error(`Audit cleanup error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  // Helper methods

  generateFingerprint(attempt) {
    const fingerprintData = {
      ipAddress: attempt.ipAddress,
      userAgent: attempt.userAgent,
      timestamp: Math.floor(Date.now() / (1000 * 60 * 5)) // 5-minute windows
    };

    return crypto
      .createHash('sha256')
      .update(JSON.stringify(fingerprintData))
      .digest('hex')
      .substring(0, 16);
  }

  convertToCSV(entries) {
    if (entries.length === 0) return '';

    const headers = [
      'sessionId', 'candidateId', 'factorType', 'attemptType', 'timestamp',
      'success', 'confidence', 'error', 'ipAddress', 'fingerprint'
    ];

    const csvRows = [headers.join(',')];

    for (const entry of entries) {
      const row = [
        entry.sessionId,
        entry.candidateId,
        entry.factorType,
        entry.attemptType,
        entry.timestamp.toISOString(),
        entry.details.success,
        entry.details.confidence || '',
        entry.details.error || '',
        entry.ipAddress || '',
        entry.fingerprint || ''
      ];

      csvRows.push(row.map(field => `"${String(field).replace(/"/g, '""')}"`).join(','));
    }

    return csvRows.join('\n');
  }

  /**
   * Get audit service statistics
   */
  getServiceStatistics() {
    const totalSessions = this.auditLogs.size;
    let totalEntries = 0;
    let oldestEntry = null;
    let newestEntry = null;

    for (const sessionLogs of this.auditLogs.values()) {
      totalEntries += sessionLogs.length;

      for (const entry of sessionLogs) {
        if (!oldestEntry || entry.timestamp < oldestEntry) {
          oldestEntry = entry.timestamp;
        }
        if (!newestEntry || entry.timestamp > newestEntry) {
          newestEntry = entry.timestamp;
        }
      }
    }

    return {
      totalSessions,
      totalEntries,
      oldestEntry,
      newestEntry,
      retentionDays: this.auditConfig.retentionDays,
      maxEntriesPerSession: this.auditConfig.maxEntriesPerSession
    };
  }
}

module.exports = VerificationAuditService;