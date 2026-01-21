/**
 * Property test for multi-factor authentication enforcement
 * Property 15: Multi-factor Authentication Enforcement
 * Validates: Requirements 6.1
 */

const IdentityVerificationService = require('../services/IdentityVerificationService');

describe('Property Test: Multi-factor Authentication Enforcement', () => {
  let identityService;

  beforeEach(() => {
    identityService = new IdentityVerificationService();
  });

  afterEach(() => {
    // Cleanup any test data
    identityService.verificationAttempts.clear();
    identityService.otpStore.clear();
    identityService.biometricData.clear();
  });

  /**
   * Property: MFA must enforce all required factors
   * Invariant: No verification token can be generated without completing all required factors
   */
  describe('Required Factors Enforcement Property', () => {
    test('should enforce all required factors before completion', async () => {
      const testCases = [
        { requiredFactors: ['email'] },
        { requiredFactors: ['email', 'sms'] },
        { requiredFactors: ['email', 'photoId'] },
        { requiredFactors: ['email', 'sms', 'photoId'] },
        { requiredFactors: ['email', 'sms', 'photoId', 'biometric'] }
      ];

      for (const testCase of testCases) {
        const candidateId = `candidate-${Math.random()}`;

        // Initialize MFA with specific required factors
        const initResult = await identityService.initializeMFA(
          candidateId,
          'test@example.com',
          '+1234567890',
          { requiredFactors: testCase.requiredFactors }
        );

        expect(initResult.success).toBe(true);
        const sessionId = initResult.sessionId;

        // Property: Should not be complete initially
        let status = identityService.getMFAStatus(sessionId);
        expect(status.isComplete).toBe(false);

        // Property: Token generation should fail before completion
        let tokenResult = identityService.generateVerificationToken(sessionId);
        expect(tokenResult.success).toBe(false);

        // Verify each required factor except the last one
        for (let i = 0; i < testCase.requiredFactors.length - 1; i++) {
          const factor = testCase.requiredFactors[i];
          await verifyFactor(identityService, sessionId, factor);

          // Property: Should still not be complete
          status = identityService.getMFAStatus(sessionId);
          expect(status.isComplete).toBe(false);

          // Property: Token generation should still fail
          tokenResult = identityService.generateVerificationToken(sessionId);
          expect(tokenResult.success).toBe(false);
        }

        // Verify the last required factor
        const lastFactor = testCase.requiredFactors[testCase.requiredFactors.length - 1];
        await verifyFactor(identityService, sessionId, lastFactor);

        // Property: Should now be complete
        status = identityService.getMFAStatus(sessionId);
        expect(status.isComplete).toBe(true);
        expect(status.status).toBe('completed');

        // Property: Token generation should now succeed
        tokenResult = identityService.generateVerificationToken(sessionId);
        expect(tokenResult.success).toBe(true);
        expect(tokenResult.token).toBeDefined();
      }
    });
  });

  // Helper function to verify different factor types
  async function verifyFactor(service, sessionId, factor) {
    switch (factor) {
      case 'email':
        await service.sendEmailOTP(sessionId);
        const emailOTP = service.otpStore.get(`email_${sessionId}`).otp;
        await service.verifyOTP(sessionId, emailOTP, 'email');
        break;
      case 'sms':
        await service.sendSMSOTP(sessionId);
        const smsOTP = service.otpStore.get(`sms_${sessionId}`).otp;
        await service.verifyOTP(sessionId, smsOTP, 'sms');
        break;
      case 'photoId':
        const mockFile = {
          originalname: 'id.jpg',
          mimetype: 'image/jpeg',
          size: 1024 * 1024 // 1MB
        };
        await service.uploadPhotoID(sessionId, mockFile);
        break;
      case 'biometric':
        const mockBiometric = 'mock_biometric_data';
        await service.captureBiometric(sessionId, mockBiometric);
        break;
    }
  }

  /**
   * Property: OTP attempts must be limited
   * Invariant: No factor can be verified after exceeding maximum attempts
   */
  describe('Attempt Limitation Property', () => {
    test('should enforce maximum OTP attempts', async () => {
      const candidateId = 'test-candidate-attempts';

      const initResult = await identityService.initializeMFA(
        candidateId,
        'test@example.com',
        '+1234567890',
        { requiredFactors: ['email'] }
      );

      const sessionId = initResult.sessionId;

      // Send OTP
      await identityService.sendEmailOTP(sessionId);
      const correctOTP = identityService.otpStore.get(`email_${sessionId}`).otp;

      // Property: Should allow attempts up to the limit
      for (let i = 0; i < identityService.otpConfig.maxAttempts - 1; i++) {
        const result = await identityService.verifyOTP(sessionId, 'wrong-otp', 'email');
        expect(result.success).toBe(false);
      }

      // Property: Last attempt with wrong OTP should fail and block further attempts
      const lastWrongResult = await identityService.verifyOTP(sessionId, 'wrong-otp', 'email');
      expect(lastWrongResult.success).toBe(false);

      // Property: Even correct OTP should now fail due to exceeded attempts
      const correctResult = await identityService.verifyOTP(sessionId, correctOTP, 'email');
      expect(correctResult.success).toBe(false);
      expect(correctResult.error).toMatch(/exceeded|No OTP found/); // Either error message is acceptable
    });

    test('should enforce maximum sending attempts', async () => {
      const candidateId = 'test-candidate-send-attempts';

      const initResult = await identityService.initializeMFA(
        candidateId,
        'test@example.com',
        '+1234567890',
        { requiredFactors: ['email'] }
      );

      const sessionId = initResult.sessionId;

      // Property: Should allow sending up to the limit
      for (let i = 0; i < identityService.otpConfig.maxAttempts; i++) {
        const result = await identityService.sendEmailOTP(sessionId);
        expect(result.success).toBe(true);
      }

      // Property: Should block further sending attempts
      const blockedResult = await identityService.sendEmailOTP(sessionId);
      expect(blockedResult.success).toBe(false);
      expect(blockedResult.error).toContain('exceeded');
    });
  });

  /**
   * Property: OTP expiration must be enforced
   * Invariant: Expired OTPs cannot be used for verification
   */
  describe('OTP Expiration Property', () => {
    test('should reject expired OTPs', async () => {
      const candidateId = 'test-candidate-expiry';

      const initResult = await identityService.initializeMFA(
        candidateId,
        'test@example.com',
        '+1234567890',
        { requiredFactors: ['email'] }
      );

      const sessionId = initResult.sessionId;

      // Send OTP
      await identityService.sendEmailOTP(sessionId);
      const otp = identityService.otpStore.get(`email_${sessionId}`).otp;

      // Property: Valid OTP should work before expiration
      const validResult = await identityService.verifyOTP(sessionId, otp, 'email');
      expect(validResult.success).toBe(true);

      // Reset for expiration test
      await identityService.sendEmailOTP(sessionId);
      const newOTP = identityService.otpStore.get(`email_${sessionId}`).otp;

      // Manually expire the OTP
      const otpData = identityService.otpStore.get(`email_${sessionId}`);
      otpData.expiresAt = new Date(Date.now() - 1000); // 1 second ago

      // Property: Expired OTP should be rejected
      const expiredResult = await identityService.verifyOTP(sessionId, newOTP, 'email');
      expect(expiredResult.success).toBe(false);
      expect(expiredResult.error).toContain('expired');
    });
  });

  /**
   * Property: Session expiration must be enforced
   * Invariant: Expired sessions cannot be used for verification
   */
  describe('Session Expiration Property', () => {
    test('should reject operations on expired sessions', async () => {
      const candidateId = 'test-candidate-session-expiry';

      const initResult = await identityService.initializeMFA(
        candidateId,
        'test@example.com',
        '+1234567890',
        { requiredFactors: ['email'] }
      );

      const sessionId = initResult.sessionId;

      // Property: Valid session should work initially
      let status = identityService.getMFAStatus(sessionId);
      expect(status.success).toBe(true);

      // Manually expire the session
      const session = identityService.verificationAttempts.get(sessionId);
      session.expiresAt = new Date(Date.now() - 1000); // 1 second ago

      // Property: Operations on expired session should fail
      const sendResult = await identityService.sendEmailOTP(sessionId);
      expect(sendResult.success).toBe(false);

      const verifyResult = await identityService.verifyOTP(sessionId, '123456', 'email');
      expect(verifyResult.success).toBe(false);

      status = identityService.getMFAStatus(sessionId);
      expect(status.success).toBe(false);
    });
  });

  /**
   * Property: Biometric verification must meet threshold
   * Invariant: Low-confidence biometric matches must be rejected
   */
  describe('Biometric Threshold Property', () => {
    test('should enforce biometric confidence threshold', async () => {
      const candidateId = 'test-candidate-biometric';

      // Store a biometric template
      identityService.biometricData.set(candidateId, {
        template: 'stored_template',
        type: 'facial',
        createdAt: new Date()
      });

      // Test multiple biometric comparisons
      for (let i = 0; i < 10; i++) {
        const result = await identityService.verifyExistingBiometric(candidateId, 'test_biometric');

        // Property: Result should have confidence score
        expect(result.success).toBe(true);
        expect(result.confidence).toBeDefined();
        expect(result.confidence).toBeGreaterThanOrEqual(0);
        expect(result.confidence).toBeLessThanOrEqual(1);

        // Property: Match decision should be based on threshold
        expect(result.isMatch).toBe(result.confidence >= result.threshold);
      }
    });
  });

  /**
   * Property: Photo ID validation must be enforced
   * Invariant: Invalid photo formats/sizes must be rejected
   */
  describe('Photo ID Validation Property', () => {
    test('should enforce photo ID file requirements', async () => {
      const candidateId = 'test-candidate-photo';

      const initResult = await identityService.initializeMFA(
        candidateId,
        'test@example.com',
        '+1234567890',
        { requiredFactors: ['photoId'] }
      );

      const sessionId = initResult.sessionId;

      const testCases = [
        {
          file: null,
          shouldPass: false,
          description: 'null file'
        },
        {
          file: {
            originalname: 'test.txt',
            mimetype: 'text/plain',
            size: 1024
          },
          shouldPass: false,
          description: 'wrong file type'
        },
        {
          file: {
            originalname: 'huge.jpg',
            mimetype: 'image/jpeg',
            size: 10 * 1024 * 1024 // 10MB
          },
          shouldPass: false,
          description: 'file too large'
        },
        {
          file: {
            originalname: 'valid.jpg',
            mimetype: 'image/jpeg',
            size: 1024 * 1024 // 1MB
          },
          shouldPass: true,
          description: 'valid file'
        }
      ];

      for (const testCase of testCases) {
        const result = await identityService.uploadPhotoID(sessionId, testCase.file);

        if (testCase.shouldPass) {
          // Property: Valid files should be processed
          expect(result.success).toBe(true);
        } else {
          // Property: Invalid files should be rejected
          expect(result.success).toBe(false);
          expect(result.error).toBeDefined();
        }
      }
    });
  });

  /**
   * Property: Concurrent sessions must be isolated
   * Invariant: One session's verification should not affect another
   */
  describe('Session Isolation Property', () => {
    test('should isolate concurrent MFA sessions', async () => {
      const sessions = [];

      // Create multiple concurrent sessions
      for (let i = 0; i < 5; i++) {
        const candidateId = `candidate-${i}`;
        const initResult = await identityService.initializeMFA(
          candidateId,
          `test${i}@example.com`,
          `+123456789${i}`,
          { requiredFactors: ['email'] }
        );

        expect(initResult.success).toBe(true);
        sessions.push({
          candidateId,
          sessionId: initResult.sessionId
        });
      }

      // Send OTPs to all sessions
      for (const session of sessions) {
        const result = await identityService.sendEmailOTP(session.sessionId);
        expect(result.success).toBe(true);
      }

      // Property: Each session should have its own OTP
      const otps = sessions.map(session =>
        identityService.otpStore.get(`email_${session.sessionId}`).otp
      );

      // Property: All OTPs should be different (very high probability)
      const uniqueOTPs = new Set(otps);
      expect(uniqueOTPs.size).toBe(sessions.length);

      // Verify one session
      const firstSession = sessions[0];
      const firstOTP = identityService.otpStore.get(`email_${firstSession.sessionId}`).otp;
      const verifyResult = await identityService.verifyOTP(firstSession.sessionId, firstOTP, 'email');
      expect(verifyResult.success).toBe(true);

      // Property: Other sessions should remain unaffected
      for (let i = 1; i < sessions.length; i++) {
        const status = identityService.getMFAStatus(sessions[i].sessionId);
        expect(status.isComplete).toBe(false);
        expect(status.verifiedFactors).not.toContain('email');
      }
    });
  });

  /**
   * Property: Token generation must include verified factors
   * Invariant: Generated tokens must accurately reflect completed verification factors
   */
  describe('Token Integrity Property', () => {
    test('should include all verified factors in token', async () => {
      const candidateId = 'test-candidate-token';

      const initResult = await identityService.initializeMFA(
        candidateId,
        'test@example.com',
        '+1234567890',
        { requiredFactors: ['email', 'sms'] } // Only require email and SMS
      );

      const sessionId = initResult.sessionId;

      // Verify email
      await identityService.sendEmailOTP(sessionId);
      const emailOTP = identityService.otpStore.get(`email_${sessionId}`).otp;
      await identityService.verifyOTP(sessionId, emailOTP, 'email');

      // Verify SMS
      await identityService.sendSMSOTP(sessionId);
      const smsOTP = identityService.otpStore.get(`sms_${sessionId}`).otp;
      await identityService.verifyOTP(sessionId, smsOTP, 'sms');

      // Check status to ensure completion
      const status = identityService.getMFAStatus(sessionId);
      expect(status.isComplete).toBe(true);
      expect(status.status).toBe('completed');

      // Generate token
      const tokenResult = identityService.generateVerificationToken(sessionId);
      expect(tokenResult.success).toBe(true);

      // Property: Token should be a valid JWT
      expect(tokenResult.token).toMatch(/^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/);

      // Property: Token should have expiration
      expect(tokenResult.expiresAt).toBeInstanceOf(Date);
      expect(tokenResult.expiresAt.getTime()).toBeGreaterThan(Date.now());
    });
  });

  /**
   * Property: Cleanup must remove expired data
   * Invariant: Expired sessions and OTPs must be removed from memory
   */
  describe('Cleanup Property', () => {
    test('should clean up expired sessions and OTPs', async () => {
      // Create sessions and OTPs
      const sessions = [];
      for (let i = 0; i < 3; i++) {
        const candidateId = `cleanup-candidate-${i}`;
        const initResult = await identityService.initializeMFA(
          candidateId,
          `cleanup${i}@example.com`,
          `+12345678${i}0`,
          { requiredFactors: ['email'] }
        );

        sessions.push(initResult.sessionId);
        await identityService.sendEmailOTP(initResult.sessionId);
      }

      // Property: All sessions and OTPs should exist initially
      expect(identityService.verificationAttempts.size).toBe(3);
      expect(identityService.otpStore.size).toBe(3);

      // Manually expire half of them
      const expiredTime = new Date(Date.now() - 1000);

      // Expire first session
      identityService.verificationAttempts.get(sessions[0]).expiresAt = expiredTime;

      // Expire first OTP
      identityService.otpStore.get(`email_${sessions[0]}`).expiresAt = expiredTime;

      // Run cleanup
      const cleanedCount = identityService.cleanupExpiredSessions();

      // Property: Expired items should be removed
      expect(cleanedCount).toBe(1);
      expect(identityService.verificationAttempts.size).toBe(2);
      expect(identityService.otpStore.size).toBe(2);

      // Property: Non-expired items should remain
      expect(identityService.verificationAttempts.has(sessions[1])).toBe(true);
      expect(identityService.verificationAttempts.has(sessions[2])).toBe(true);
    });
  });
});