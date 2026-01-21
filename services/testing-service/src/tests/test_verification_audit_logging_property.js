/**
 * Property test for verification audit logging
 * Property 17: Verification Audit Logging
 * Validates: Requirements 6.6
 */

const VerificationAuditService = require('../services/VerificationAuditService');
const IdentityVerificationService = require('../services/IdentityVerificationService');

describe('Property Test: Verification Audit Logging', () => {
  let auditService;
  let identityService;

  beforeEach(() => {
    auditService = new VerificationAuditService();
    identityService = new IdentityVerificationService();
  });

  afterEach(() => {
    // Cleanup test data
    auditService.auditLogs.clear();
    identityService.verificationAttempts.clear();
    identityService.otpStore.clear();
  });

  /**
   * Property: All verification attempts must be logged
   * Invariant: Every verification operation must create an audit entry
   */
  describe('Complete Audit Trail Property', () => {
    test('should log all verification attempts with complete audit trail', async () => {
      const candidateId = 'audit-test-candidate';
      const sessionId = 'audit-test-session';

      // Initialize MFA session
      const initResult = await identityService.initializeMFA(
        candidateId,
        'test@example.com',
        '+1234567890',
        {
          requiredFactors: ['email', 'photoId'],
          ipAddress: '192.168.1.100',
          userAgent: 'Mozilla/5.0 Test Browser'
        }
      );

      expect(initResult.success).toBe(true);
      const actualSessionId = initResult.sessionId;

      // Property: Session initialization should be logged
      const sessionAudit = identityService.auditService.getSessionAuditTrail(actualSessionId);
      expect(sessionAudit.success).toBe(true);
      expect(sessionAudit.entries.length).toBeGreaterThan(0);

      const initEntry = sessionAudit.entries.find(entry => entry.attemptType === 'initiate');
      expect(initEntry).toBeDefined();
      expect(initEntry.factorType).toBe('session');
      expect(initEntry.success).toBe(true);

      // Send email OTP
      await identityService.sendEmailOTP(actualSessionId);

      // Property: OTP generation should be logged
      const afterOTPAudit = identityService.auditService.getSessionAuditTrail(actualSessionId);
      const otpGenEntry = afterOTPAudit.entries.find(entry => entry.attemptType === 'otp_generate');
      expect(otpGenEntry).toBeDefined();
      expect(otpGenEntry.factorType).toBe('email');
      expect(otpGenEntry.success).toBe(true);

      // Verify email OTP
      const emailOTP = identityService.otpStore.get(`email_${actualSessionId}`).otp;
      await identityService.verifyOTP(actualSessionId, emailOTP, 'email');

      // Property: OTP verification should be logged
      const afterVerifyAudit = identityService.auditService.getSessionAuditTrail(actualSessionId);
      const otpVerifyEntry = afterVerifyAudit.entries.find(entry => entry.attemptType === 'otp_verify');
      expect(otpVerifyEntry).toBeDefined();
      expect(otpVerifyEntry.factorType).toBe('email');
      expect(otpVerifyEntry.success).toBe(true);

      // Upload photo ID
      const mockFile = {
        originalname: 'id.jpg',
        mimetype: 'image/jpeg',
        size: 1024 * 1024
      };
      await identityService.uploadPhotoID(actualSessionId, mockFile);

      // Property: Photo ID verification should be logged
      const afterPhotoAudit = identityService.auditService.getSessionAuditTrail(actualSessionId);
      const photoEntry = afterPhotoAudit.entries.find(entry => entry.attemptType === 'photo_verify');
      expect(photoEntry).toBeDefined();
      expect(photoEntry.factorType).toBe('photoId');
      expect(photoEntry.success).toBe(true);
      expect(photoEntry.confidence).toBeDefined();

      // Generate token
      const tokenResult = identityService.generateVerificationToken(actualSessionId);
      expect(tokenResult.success).toBe(true);

      // Property: Token generation should be logged
      const finalAudit = identityService.auditService.getSessionAuditTrail(actualSessionId);
      const tokenEntry = finalAudit.entries.find(entry => entry.attemptType === 'generate');
      expect(tokenEntry).toBeDefined();
      expect(tokenEntry.factorType).toBe('token');
      expect(tokenEntry.success).toBe(true);

      // Property: MFA completion should be logged
      const completeEntry = finalAudit.entries.find(entry => entry.attemptType === 'complete');
      expect(completeEntry).toBeDefined();
      expect(completeEntry.factorType).toBe('session');
      expect(completeEntry.success).toBe(true);

      // Property: All entries should have timestamps in chronological order
      const timestamps = finalAudit.entries.map(entry => entry.timestamp);
      for (let i = 1; i < timestamps.length; i++) {
        expect(timestamps[i]).toBeInstanceOf(Date);
        expect(timestamps[i].getTime()).toBeGreaterThanOrEqual(timestamps[i - 1].getTime());
      }
    });

    test('should log failed verification attempts', async () => {
      const candidateId = 'audit-fail-candidate';

      const initResult = await identityService.initializeMFA(
        candidateId,
        'test@example.com',
        '+1234567890',
        { requiredFactors: ['email'] }
      );

      const sessionId = initResult.sessionId;

      // Send OTP
      await identityService.sendEmailOTP(sessionId);

      // Attempt wrong OTP multiple times
      for (let i = 0; i < 3; i++) {
        await identityService.verifyOTP(sessionId, 'wrong-otp', 'email');
      }

      // Property: All failed attempts should be logged
      const auditTrail = identityService.auditService.getSessionAuditTrail(sessionId);
      const failedAttempts = auditTrail.entries.filter(entry =>
        entry.attemptType === 'otp_verify' && !entry.success
      );

      expect(failedAttempts.length).toBe(3);

      // Property: Each failed attempt should have error information
      for (const attempt of failedAttempts) {
        expect(attempt.error).toBeDefined();
        expect(attempt.error).toContain('Invalid OTP');
        expect(attempt.metadata.attemptNumber).toBeDefined();
        expect(attempt.metadata.remainingAttempts).toBeDefined();
      }
    });
  });

  /**
   * Property: Audit entries must be immutable
   * Invariant: Once logged, audit entries cannot be modified
   */
  describe('Audit Immutability Property', () => {
    test('should maintain immutable audit entries', () => {
      const sessionId = 'immutable-test-session';
      const candidateId = 'immutable-test-candidate';

      // Log initial entry
      const logResult = auditService.logVerificationAttempt(sessionId, candidateId, 'email', {
        type: 'otp_verify',
        success: true,
        metadata: { originalValue: 'test' }
      });

      expect(logResult.success).toBe(true);
      const auditId = logResult.auditId;

      // Get audit trail
      const auditTrail = auditService.getSessionAuditTrail(sessionId);
      const originalEntry = auditTrail.entries[0];

      // Property: Entry should have all required fields
      expect(originalEntry.id).toBe(auditId);
      expect(originalEntry.factorType).toBe('email');
      expect(originalEntry.attemptType).toBe('otp_verify');
      expect(originalEntry.success).toBe(true);
      expect(originalEntry.metadata.originalValue).toBe('test');

      // Attempt to modify the returned entry (should not affect stored entry)
      originalEntry.success = false;
      originalEntry.metadata.originalValue = 'modified';

      // Property: Stored entry should remain unchanged
      const auditTrailAfter = auditService.getSessionAuditTrail(sessionId);
      const storedEntry = auditTrailAfter.entries[0];

      expect(storedEntry.id).toBe(auditId);
      expect(storedEntry.success).toBe(true);
      expect(storedEntry.metadata.originalValue).toBe('test');
    });
  });

  /**
   * Property: Audit entries must have unique identifiers
   * Invariant: No two audit entries can have the same ID
   */
  describe('Unique Identifier Property', () => {
    test('should generate unique audit IDs', () => {
      const sessionId = 'unique-id-test-session';
      const candidateId = 'unique-id-test-candidate';
      const auditIds = new Set();

      // Generate multiple audit entries
      for (let i = 0; i < 100; i++) {
        const logResult = auditService.logVerificationAttempt(sessionId, candidateId, 'email', {
          type: 'test',
          success: true,
          metadata: { iteration: i }
        });

        expect(logResult.success).toBe(true);

        // Property: Each audit ID should be unique
        expect(auditIds.has(logResult.auditId)).toBe(false);
        auditIds.add(logResult.auditId);
      }

      // Property: All IDs should be different
      expect(auditIds.size).toBe(100);
    });
  });

  /**
   * Property: Audit statistics must be accurate
   * Invariant: Statistics must correctly reflect the actual audit data
   */
  describe('Statistics Accuracy Property', () => {
    test('should provide accurate verification statistics', async () => {
      const testData = [
        { candidateId: 'stats-candidate-1', factors: ['email'], shouldComplete: true },
        { candidateId: 'stats-candidate-2', factors: ['email', 'sms'], shouldComplete: true },
        { candidateId: 'stats-candidate-3', factors: ['email'], shouldComplete: false },
        { candidateId: 'stats-candidate-4', factors: ['photoId'], shouldComplete: true }
      ];

      const sessionIds = [];

      for (const testCase of testData) {
        const initResult = await identityService.initializeMFA(
          testCase.candidateId,
          'test@example.com',
          '+1234567890',
          { requiredFactors: testCase.factors }
        );

        sessionIds.push(initResult.sessionId);

        if (testCase.shouldComplete) {
          // Complete all required factors
          for (const factor of testCase.factors) {
            if (factor === 'email') {
              await identityService.sendEmailOTP(initResult.sessionId);
              const otp = identityService.otpStore.get(`email_${initResult.sessionId}`).otp;
              await identityService.verifyOTP(initResult.sessionId, otp, 'email');
            } else if (factor === 'sms') {
              await identityService.sendSMSOTP(initResult.sessionId);
              const otp = identityService.otpStore.get(`sms_${initResult.sessionId}`).otp;
              await identityService.verifyOTP(initResult.sessionId, otp, 'sms');
            } else if (factor === 'photoId') {
              const mockFile = { originalname: 'id.jpg', mimetype: 'image/jpeg', size: 1024 * 1024 };
              await identityService.uploadPhotoID(initResult.sessionId, mockFile);
            }
          }

          // Trigger completion check by calling getMFAStatus
          const status = identityService.getMFAStatus(initResult.sessionId);
          expect(status.isComplete).toBe(true);
        } else {
          // Fail verification
          await identityService.sendEmailOTP(initResult.sessionId);
          await identityService.verifyOTP(initResult.sessionId, 'wrong-otp', 'email');
        }
      }

      // Get statistics
      const stats = identityService.auditService.getVerificationStatistics();
      expect(stats.success).toBe(true);

      // Property: Total sessions should match test data
      expect(stats.statistics.totalSessions).toBe(testData.length);

      // Property: Completed sessions should match successful test cases
      const expectedCompleted = testData.filter(tc => tc.shouldComplete).length;
      expect(stats.statistics.completedSessions).toBe(expectedCompleted);

      // Property: Failed sessions should match failed test cases
      const expectedFailed = testData.filter(tc => !tc.shouldComplete).length;
      expect(stats.statistics.failedSessions).toBe(expectedFailed);

      // Property: Success rate should be calculated correctly
      const expectedSuccessRate = Math.round((expectedCompleted / testData.length) * 100);
      expect(stats.statistics.overallSuccessRate).toBe(expectedSuccessRate);

      // Property: Factor statistics should reflect actual attempts
      expect(stats.statistics.factorStats.email.attempts).toBeGreaterThan(0);
      expect(stats.statistics.factorStats.email.successes).toBeGreaterThan(0);
      expect(stats.statistics.factorStats.email.failures).toBeGreaterThan(0);
    });
  });

  /**
   * Property: Audit export must preserve data integrity
   * Invariant: Exported data must match the original audit entries
   */
  describe('Export Data Integrity Property', () => {
    test('should maintain data integrity during export', () => {
      const sessionId = 'export-test-session';
      const candidateId = 'export-test-candidate';

      // Create test audit entries
      const testEntries = [
        { type: 'initiate', factorType: 'session', success: true },
        { type: 'otp_generate', factorType: 'email', success: true },
        { type: 'otp_verify', factorType: 'email', success: true },
        { type: 'complete', factorType: 'session', success: true }
      ];

      const originalIds = [];
      for (const entry of testEntries) {
        const logResult = auditService.logVerificationAttempt(sessionId, candidateId, entry.factorType, {
          type: entry.type,
          success: entry.success,
          metadata: { testData: true }
        });
        originalIds.push(logResult.auditId);
      }

      // Export as JSON
      const jsonExport = auditService.exportAuditLogs('json');
      expect(jsonExport.success).toBe(true);
      expect(jsonExport.totalRecords).toBe(testEntries.length);

      const exportedData = JSON.parse(jsonExport.data);

      // Property: Exported data should match original entries
      expect(exportedData.length).toBe(testEntries.length);

      for (let i = 0; i < exportedData.length; i++) {
        const exported = exportedData[i];
        const original = testEntries[i];

        expect(exported.sessionId).toBe(sessionId);
        expect(exported.candidateId).toBe(candidateId);
        expect(exported.factorType).toBe(original.factorType);
        expect(exported.attemptType).toBe(original.type);
        expect(exported.details.success).toBe(original.success);
        expect(exported.details.metadata.testData).toBe(true);
      }

      // Export as CSV
      const csvExport = auditService.exportAuditLogs('csv');
      expect(csvExport.success).toBe(true);
      expect(csvExport.totalRecords).toBe(testEntries.length);

      const csvLines = csvExport.data.split('\n');
      expect(csvLines.length).toBe(testEntries.length + 1); // +1 for header

      // Property: CSV should have proper header
      const header = csvLines[0];
      expect(header).toContain('sessionId');
      expect(header).toContain('candidateId');
      expect(header).toContain('factorType');
      expect(header).toContain('attemptType');
      expect(header).toContain('success');
    });
  });

  /**
   * Property: Audit cleanup must preserve recent entries
   * Invariant: Only expired entries should be removed during cleanup
   */
  describe('Cleanup Preservation Property', () => {
    test('should only remove expired entries during cleanup', () => {
      const sessionId = 'cleanup-test-session';
      const candidateId = 'cleanup-test-candidate';

      // Create entries with different ages
      const recentEntry = auditService.logVerificationAttempt(sessionId, candidateId, 'email', {
        type: 'recent',
        success: true
      });

      // Manually create an old entry by modifying the audit log
      const oldEntryId = auditService.logVerificationAttempt(sessionId, candidateId, 'email', {
        type: 'old',
        success: true
      });

      // Modify the timestamp to make it old
      const sessionLogs = auditService.auditLogs.get(sessionId);
      const oldEntry = sessionLogs.find(entry => entry.attemptType === 'old');
      if (oldEntry) {
        const oldDate = new Date();
        oldDate.setDate(oldDate.getDate() - 400); // 400 days ago (beyond retention)
        oldEntry.timestamp = oldDate;
      }

      // Property: Before cleanup, both entries should exist
      const beforeCleanup = auditService.getSessionAuditTrail(sessionId);
      expect(beforeCleanup.entries.length).toBe(2);

      // Run cleanup
      const cleanupResult = auditService.cleanupExpiredLogs();
      expect(cleanupResult.success).toBe(true);
      expect(cleanupResult.cleanedCount).toBe(1);

      // Property: After cleanup, only recent entry should remain
      const afterCleanup = auditService.getSessionAuditTrail(sessionId);
      expect(afterCleanup.entries.length).toBe(1);
      expect(afterCleanup.entries[0].attemptType).toBe('recent');
    });
  });

  /**
   * Property: Candidate audit trail must be complete and accurate
   * Invariant: All entries for a candidate must be retrievable across sessions
   */
  describe('Candidate Audit Trail Property', () => {
    test('should provide complete candidate audit trail across sessions', async () => {
      const candidateId = 'multi-session-candidate';

      // Create multiple sessions for the same candidate
      const sessions = [];
      for (let i = 0; i < 3; i++) {
        const initResult = await identityService.initializeMFA(
          candidateId,
          'test@example.com',
          '+1234567890',
          { requiredFactors: ['email'] }
        );

        sessions.push(initResult.sessionId);

        // Complete verification for each session
        await identityService.sendEmailOTP(initResult.sessionId);
        const otp = identityService.otpStore.get(`email_${initResult.sessionId}`).otp;
        await identityService.verifyOTP(initResult.sessionId, otp, 'email');

        // Trigger completion check
        const status = identityService.getMFAStatus(initResult.sessionId);
        expect(status.isComplete).toBe(true);
      }

      // Get candidate audit trail
      const candidateAudit = identityService.auditService.getCandidateAuditTrail(candidateId);
      expect(candidateAudit.success).toBe(true);

      // Property: Should have entries from all sessions
      const sessionIdsInAudit = new Set(candidateAudit.entries.map(entry => entry.sessionId));
      expect(sessionIdsInAudit.size).toBe(3);

      for (const sessionId of sessions) {
        expect(sessionIdsInAudit.has(sessionId)).toBe(true);
      }

      // Property: Should have expected entry types for each session
      const expectedEntryTypes = ['initiate', 'otp_generate', 'otp_verify', 'complete'];
      for (const sessionId of sessions) {
        const sessionEntries = candidateAudit.entries.filter(entry => entry.sessionId === sessionId);
        const entryTypes = sessionEntries.map(entry => entry.attemptType);

        for (const expectedType of expectedEntryTypes) {
          expect(entryTypes).toContain(expectedType);
        }
      }

      // Property: Entries should be sorted by timestamp (newest first)
      const timestamps = candidateAudit.entries.map(entry => entry.timestamp);
      for (let i = 1; i < timestamps.length; i++) {
        expect(timestamps[i].getTime()).toBeLessThanOrEqual(timestamps[i - 1].getTime());
      }
    });

    test('should support filtering candidate audit trail', async () => {
      const candidateId = 'filter-test-candidate';

      const initResult = await identityService.initializeMFA(
        candidateId,
        'test@example.com',
        '+1234567890',
        { requiredFactors: ['email', 'photoId'] }
      );

      const sessionId = initResult.sessionId;

      // Complete email verification
      await identityService.sendEmailOTP(sessionId);
      const otp = identityService.otpStore.get(`email_${sessionId}`).otp;
      await identityService.verifyOTP(sessionId, otp, 'email');

      // Complete photo ID verification
      const mockFile = { originalname: 'id.jpg', mimetype: 'image/jpeg', size: 1024 * 1024 };
      await identityService.uploadPhotoID(sessionId, mockFile);

      // Property: Filter by factor type should return only matching entries
      const emailAudit = identityService.auditService.getCandidateAuditTrail(candidateId, { factorType: 'email' });
      expect(emailAudit.success).toBe(true);

      for (const entry of emailAudit.entries) {
        expect(entry.factorType).toBe('email');
      }

      const photoAudit = identityService.auditService.getCandidateAuditTrail(candidateId, { factorType: 'photoId' });
      expect(photoAudit.success).toBe(true);

      for (const entry of photoAudit.entries) {
        expect(entry.factorType).toBe('photoId');
      }

      // Property: Filter by attempt type should return only matching entries
      const verifyAudit = identityService.auditService.getCandidateAuditTrail(candidateId, { attemptType: 'otp_verify' });
      expect(verifyAudit.success).toBe(true);

      for (const entry of verifyAudit.entries) {
        expect(entry.attemptType).toBe('otp_verify');
      }
    });
  });

  /**
   * Property: Audit service must handle concurrent operations safely
   * Invariant: Concurrent logging operations should not corrupt audit data
   */
  describe('Concurrency Safety Property', () => {
    test('should handle concurrent audit logging safely', async () => {
      const candidateId = 'concurrent-test-candidate';
      const numConcurrentOps = 50;

      // Create concurrent logging operations
      const promises = [];
      for (let i = 0; i < numConcurrentOps; i++) {
        const sessionId = `concurrent-session-${i}`;
        const promise = identityService.auditService.logVerificationAttempt(sessionId, candidateId, 'email', {
          type: 'concurrent_test',
          success: true,
          metadata: { operationId: i }
        });
        promises.push(promise);
      }

      // Wait for all operations to complete
      const results = await Promise.all(promises);

      // Property: All operations should succeed
      for (const result of results) {
        expect(result.success).toBe(true);
        expect(result.auditId).toBeDefined();
      }

      // Property: All audit IDs should be unique
      const auditIds = results.map(result => result.auditId);
      const uniqueIds = new Set(auditIds);
      expect(uniqueIds.size).toBe(numConcurrentOps);

      // Property: All entries should be retrievable
      const candidateAudit = identityService.auditService.getCandidateAuditTrail(candidateId);
      expect(candidateAudit.success).toBe(true);
      expect(candidateAudit.entries.length).toBe(numConcurrentOps);

      // Property: All operation IDs should be present
      const operationIds = candidateAudit.entries.map(entry => entry.metadata.operationId);
      const uniqueOpIds = new Set(operationIds);
      expect(uniqueOpIds.size).toBe(numConcurrentOps);
    });
  });
});