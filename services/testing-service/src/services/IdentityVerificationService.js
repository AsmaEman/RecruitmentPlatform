/**
 * Identity verification service with multi-factor authentication
 * Requirements: 6.1, 6.2, 6.3, 6.5
 */

const crypto = require('crypto');
const jwt = require('jsonwebtoken');
const multer = require('multer');
const path = require('path');

class IdentityVerificationService {
  constructor() {
    this.logger = require('../utils/logger');
    this.auditService = new (require('./VerificationAuditService'))();
    this.otpStore = new Map(); // In production, use Redis
    this.verificationAttempts = new Map();
    this.biometricData = new Map();

    // OTP configuration
    this.otpConfig = {
      length: 6,
      expiryMinutes: 5,
      maxAttempts: 3
    };

    // Photo ID verification settings
    this.photoIdConfig = {
      allowedTypes: ['image/jpeg', 'image/png', 'image/jpg'],
      maxSize: 5 * 1024 * 1024, // 5MB
      minWidth: 800,
      minHeight: 600
    };
  }

  /**
   * Initialize MFA for a candidate
   */
  async initializeMFA(candidateId, email, phoneNumber, options = {}) {
    try {
      const sessionId = crypto.randomUUID();
      const timestamp = new Date();

      const mfaSession = {
        sessionId,
        candidateId,
        email,
        phoneNumber,
        status: 'pending',
        factors: {
          email: { verified: false, attempts: 0 },
          sms: { verified: false, attempts: 0 },
          photoId: { verified: false, attempts: 0 },
          biometric: { verified: false, attempts: 0 }
        },
        requiredFactors: options.requiredFactors || ['email', 'photoId'],
        createdAt: timestamp,
        expiresAt: new Date(timestamp.getTime() + (30 * 60 * 1000)), // 30 minutes
        ipAddress: options.ipAddress,
        userAgent: options.userAgent
      };

      this.verificationAttempts.set(sessionId, mfaSession);

      // Log session initialization
      this.auditService.logSessionInitialization(sessionId, candidateId, mfaSession.requiredFactors, {
        ipAddress: options.ipAddress,
        userAgent: options.userAgent
      });

      this.logger.info(`MFA session initialized for candidate ${candidateId}`);

      return {
        success: true,
        sessionId,
        requiredFactors: mfaSession.requiredFactors,
        expiresAt: mfaSession.expiresAt
      };

    } catch (error) {
      this.logger.error(`MFA initialization error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Generate and send OTP via email
   */
  async sendEmailOTP(sessionId) {
    try {
      const session = this.verificationAttempts.get(sessionId);
      if (!session) {
        throw new Error('Invalid session ID');
      }

      // Check if session is expired
      if (new Date() > session.expiresAt) {
        throw new Error('Session has expired');
      }

      if (session.factors.email.attempts >= this.otpConfig.maxAttempts) {
        throw new Error('Maximum email OTP attempts exceeded');
      }

      // Generate OTP
      const otp = this.generateOTP();
      const expiresAt = new Date(Date.now() + (this.otpConfig.expiryMinutes * 60 * 1000));

      // Store OTP
      const otpKey = `email_${sessionId}`;
      this.otpStore.set(otpKey, {
        otp,
        expiresAt,
        attempts: 0
      });

      // In production, integrate with email service (SendGrid, SES, etc.)
      await this.sendEmail(session.email, otp);

      // Update session
      session.factors.email.attempts++;
      session.factors.email.lastSentAt = new Date();

      // Log OTP generation
      this.auditService.logOTPGeneration(sessionId, session.candidateId, 'email', {
        otpLength: this.otpConfig.length,
        expiryMinutes: this.otpConfig.expiryMinutes,
        ipAddress: session.ipAddress,
        userAgent: session.userAgent
      });

      this.logger.info(`Email OTP sent to candidate ${session.candidateId}`);

      return {
        success: true,
        message: 'OTP sent to email',
        expiresAt
      };

    } catch (error) {
      this.logger.error(`Email OTP error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Generate and send OTP via SMS
   */
  async sendSMSOTP(sessionId) {
    try {
      const session = this.verificationAttempts.get(sessionId);
      if (!session) {
        throw new Error('Invalid session ID');
      }

      // Check if session is expired
      if (new Date() > session.expiresAt) {
        throw new Error('Session has expired');
      }

      if (session.factors.sms.attempts >= this.otpConfig.maxAttempts) {
        throw new Error('Maximum SMS OTP attempts exceeded');
      }

      // Generate OTP
      const otp = this.generateOTP();
      const expiresAt = new Date(Date.now() + (this.otpConfig.expiryMinutes * 60 * 1000));

      // Store OTP
      const otpKey = `sms_${sessionId}`;
      this.otpStore.set(otpKey, {
        otp,
        expiresAt,
        attempts: 0
      });

      // In production, integrate with SMS service (Twilio, AWS SNS, etc.)
      await this.sendSMS(session.phoneNumber, otp);

      // Update session
      session.factors.sms.attempts++;
      session.factors.sms.lastSentAt = new Date();

      // Log OTP generation
      this.auditService.logOTPGeneration(sessionId, session.candidateId, 'sms', {
        otpLength: this.otpConfig.length,
        expiryMinutes: this.otpConfig.expiryMinutes,
        ipAddress: session.ipAddress,
        userAgent: session.userAgent
      });

      this.logger.info(`SMS OTP sent to candidate ${session.candidateId}`);

      return {
        success: true,
        message: 'OTP sent to phone',
        expiresAt
      };

    } catch (error) {
      this.logger.error(`SMS OTP error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Verify OTP
   */
  async verifyOTP(sessionId, otp, type) {
    try {
      const session = this.verificationAttempts.get(sessionId);
      if (!session) {
        throw new Error('Invalid session ID');
      }

      // Check if session is expired
      if (new Date() > session.expiresAt) {
        throw new Error('Session has expired');
      }

      const otpKey = `${type}_${sessionId}`;
      const storedOTP = this.otpStore.get(otpKey);

      if (!storedOTP) {
        throw new Error('No OTP found for this session');
      }

      if (new Date() > storedOTP.expiresAt) {
        this.otpStore.delete(otpKey);
        throw new Error('OTP has expired');
      }

      if (storedOTP.attempts >= this.otpConfig.maxAttempts) {
        this.otpStore.delete(otpKey);
        throw new Error('Maximum OTP verification attempts exceeded');
      }

      storedOTP.attempts++;

      if (storedOTP.otp !== otp) {
        // Log failed verification
        this.auditService.logOTPVerification(sessionId, session.candidateId, type, false, 'Invalid OTP', {
          attemptNumber: storedOTP.attempts,
          remainingAttempts: this.otpConfig.maxAttempts - storedOTP.attempts,
          ipAddress: session.ipAddress,
          userAgent: session.userAgent
        });

        if (storedOTP.attempts >= this.otpConfig.maxAttempts) {
          this.otpStore.delete(otpKey);
          throw new Error('Maximum OTP verification attempts exceeded');
        }
        throw new Error('Invalid OTP');
      }

      // OTP verified successfully
      this.otpStore.delete(otpKey);
      session.factors[type].verified = true;
      session.factors[type].verifiedAt = new Date();

      // Log successful verification
      this.auditService.logOTPVerification(sessionId, session.candidateId, type, true, null, {
        attemptNumber: storedOTP.attempts,
        ipAddress: session.ipAddress,
        userAgent: session.userAgent
      });

      this.logger.info(`${type.toUpperCase()} OTP verified for candidate ${session.candidateId}`);

      return {
        success: true,
        message: `${type.toUpperCase()} verification successful`,
        factorVerified: type
      };

    } catch (error) {
      this.logger.error(`OTP verification error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Upload and verify photo ID
   */
  async uploadPhotoID(sessionId, file) {
    try {
      const session = this.verificationAttempts.get(sessionId);
      if (!session) {
        throw new Error('Invalid session ID');
      }

      if (session.factors.photoId.attempts >= this.otpConfig.maxAttempts) {
        throw new Error('Maximum photo ID attempts exceeded');
      }

      // Validate file
      const validation = this.validatePhotoID(file);
      if (!validation.isValid) {
        throw new Error(validation.error);
      }

      // In production, save to secure storage (AWS S3, etc.)
      const filename = `photo_id_${sessionId}_${Date.now()}${path.extname(file.originalname)}`;
      const filepath = path.join('/tmp/uploads', filename);

      // Mock file processing - in production, use actual file operations
      const photoIdData = {
        filename,
        filepath,
        originalName: file.originalname,
        size: file.size,
        mimeType: file.mimetype,
        uploadedAt: new Date()
      };

      // Mock ID verification - in production, integrate with ID verification service
      const verificationResult = await this.verifyPhotoID(photoIdData);

      // Update session
      session.factors.photoId.attempts++;
      session.factors.photoId.data = photoIdData;

      if (verificationResult.isValid) {
        session.factors.photoId.verified = true;
        session.factors.photoId.verifiedAt = new Date();
        session.factors.photoId.confidence = verificationResult.confidence;

        // Log successful verification
        this.auditService.logPhotoIDVerification(sessionId, session.candidateId, true, verificationResult.confidence, null, {
          fileSize: file.size,
          fileType: file.mimetype,
          ipAddress: session.ipAddress,
          userAgent: session.userAgent
        });

        this.logger.info(`Photo ID verified for candidate ${session.candidateId}`);

        return {
          success: true,
          message: 'Photo ID verification successful',
          confidence: verificationResult.confidence,
          factorVerified: 'photoId'
        };
      } else {
        // Log failed verification
        this.auditService.logPhotoIDVerification(sessionId, session.candidateId, false, verificationResult.confidence, verificationResult.reason, {
          fileSize: file.size,
          fileType: file.mimetype,
          ipAddress: session.ipAddress,
          userAgent: session.userAgent
        });

        this.logger.warn(`Photo ID verification failed for candidate ${session.candidateId}`);

        return {
          success: false,
          error: 'Photo ID verification failed',
          reason: verificationResult.reason
        };
      }

    } catch (error) {
      this.logger.error(`Photo ID upload error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Capture and verify biometric data
   */
  async captureBiometric(sessionId, biometricData, type = 'facial') {
    try {
      const session = this.verificationAttempts.get(sessionId);
      if (!session) {
        throw new Error('Invalid session ID');
      }

      if (session.factors.biometric.attempts >= this.otpConfig.maxAttempts) {
        throw new Error('Maximum biometric attempts exceeded');
      }

      // Process biometric data
      const processedData = {
        type,
        data: biometricData,
        capturedAt: new Date(),
        sessionId
      };

      // Mock biometric verification - in production, use actual biometric service
      const verificationResult = await this.verifyBiometric(processedData);

      // Update session
      session.factors.biometric.attempts++;
      session.factors.biometric.data = processedData;

      if (verificationResult.isValid) {
        session.factors.biometric.verified = true;
        session.factors.biometric.verifiedAt = new Date();
        session.factors.biometric.confidence = verificationResult.confidence;

        // Store biometric template for future verification
        this.biometricData.set(session.candidateId, {
          template: verificationResult.template,
          type,
          createdAt: new Date()
        });

        // Log successful verification
        this.auditService.logBiometricVerification(sessionId, session.candidateId, true, verificationResult.confidence, null, {
          biometricType: type,
          threshold: 0.8,
          ipAddress: session.ipAddress,
          userAgent: session.userAgent
        });

        this.logger.info(`Biometric verification successful for candidate ${session.candidateId}`);

        return {
          success: true,
          message: 'Biometric verification successful',
          confidence: verificationResult.confidence,
          factorVerified: 'biometric'
        };
      } else {
        // Log failed verification
        this.auditService.logBiometricVerification(sessionId, session.candidateId, false, verificationResult.confidence, verificationResult.reason, {
          biometricType: type,
          threshold: 0.8,
          ipAddress: session.ipAddress,
          userAgent: session.userAgent
        });

        this.logger.warn(`Biometric verification failed for candidate ${session.candidateId}`);

        return {
          success: false,
          error: 'Biometric verification failed',
          reason: verificationResult.reason
        };
      }

    } catch (error) {
      this.logger.error(`Biometric capture error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Check MFA completion status
   */
  getMFAStatus(sessionId) {
    try {
      const session = this.verificationAttempts.get(sessionId);
      if (!session) {
        throw new Error('Invalid session ID');
      }

      // Check if session is expired
      if (new Date() > session.expiresAt) {
        throw new Error('Session has expired');
      }

      const verifiedFactors = Object.keys(session.factors).filter(
        factor => session.factors[factor].verified
      );

      const requiredFactors = session.requiredFactors;
      const isComplete = requiredFactors.every(factor => verifiedFactors.includes(factor));

      if (isComplete && session.status !== 'completed') {
        session.status = 'completed';
        session.completedAt = new Date();

        // Log MFA completion
        this.auditService.logMFACompletion(sessionId, session.candidateId, true, verifiedFactors, {
          completionTime: session.completedAt - session.createdAt,
          totalAttempts: Object.values(session.factors).reduce((sum, factor) => sum + factor.attempts, 0),
          ipAddress: session.ipAddress,
          userAgent: session.userAgent
        });
      }

      return {
        success: true,
        sessionId,
        status: session.status,
        requiredFactors,
        verifiedFactors,
        isComplete,
        expiresAt: session.expiresAt,
        completedAt: session.completedAt
      };

    } catch (error) {
      this.logger.error(`MFA status error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Generate verification token after successful MFA
   */
  generateVerificationToken(sessionId) {
    try {
      const session = this.verificationAttempts.get(sessionId);
      if (!session) {
        throw new Error('Invalid session ID');
      }

      // Check and update completion status first
      const statusCheck = this.getMFAStatus(sessionId);
      if (!statusCheck.success || !statusCheck.isComplete) {
        throw new Error('MFA not completed');
      }

      const tokenPayload = {
        candidateId: session.candidateId,
        sessionId,
        verifiedFactors: Object.keys(session.factors).filter(
          factor => session.factors[factor].verified
        ),
        verifiedAt: session.completedAt,
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60) // 24 hours
      };

      const token = jwt.sign(tokenPayload, process.env.JWT_SECRET || 'default-secret');

      // Log token generation
      this.auditService.logTokenGeneration(sessionId, session.candidateId, true, null, {
        tokenExpiry: new Date(tokenPayload.exp * 1000),
        verifiedFactors: tokenPayload.verifiedFactors,
        ipAddress: session.ipAddress,
        userAgent: session.userAgent
      });

      this.logger.info(`Verification token generated for candidate ${session.candidateId}`);

      return {
        success: true,
        token,
        expiresAt: new Date(tokenPayload.exp * 1000)
      };

    } catch (error) {
      this.logger.error(`Token generation error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Verify existing biometric against stored template
   */
  async verifyExistingBiometric(candidateId, biometricData) {
    try {
      const storedBiometric = this.biometricData.get(candidateId);
      if (!storedBiometric) {
        throw new Error('No biometric template found for candidate');
      }

      // Mock biometric comparison - in production, use actual biometric matching
      const similarity = this.compareBiometrics(storedBiometric.template, biometricData);
      const threshold = 0.85; // 85% similarity threshold

      const isMatch = similarity >= threshold;

      this.logger.info(`Biometric verification for candidate ${candidateId}: ${isMatch ? 'MATCH' : 'NO MATCH'} (${similarity})`);

      return {
        success: true,
        isMatch,
        confidence: similarity,
        threshold
      };

    } catch (error) {
      this.logger.error(`Biometric verification error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  // Helper methods

  generateOTP() {
    return Math.floor(Math.random() * Math.pow(10, this.otpConfig.length))
      .toString()
      .padStart(this.otpConfig.length, '0');
  }

  async sendEmail(email, otp) {
    // Mock email sending - integrate with actual email service
    this.logger.info(`Sending email OTP ${otp} to ${email}`);
    return Promise.resolve();
  }

  async sendSMS(phoneNumber, otp) {
    // Mock SMS sending - integrate with actual SMS service
    this.logger.info(`Sending SMS OTP ${otp} to ${phoneNumber}`);
    return Promise.resolve();
  }

  validatePhotoID(file) {
    if (!file) {
      return { isValid: false, error: 'No file provided' };
    }

    if (!this.photoIdConfig.allowedTypes.includes(file.mimetype)) {
      return { isValid: false, error: 'Invalid file type' };
    }

    if (file.size > this.photoIdConfig.maxSize) {
      return { isValid: false, error: 'File too large' };
    }

    return { isValid: true };
  }

  async verifyPhotoID(photoIdData) {
    // Mock ID verification - integrate with actual ID verification service
    // For testing, always return valid for properly formatted files
    const confidence = Math.random() * 0.25 + 0.75; // 75-100% confidence
    const isValid = true; // Always valid for testing

    return {
      isValid,
      confidence,
      reason: isValid ? 'ID verified successfully' : 'ID verification failed'
    };
  }

  async verifyBiometric(biometricData) {
    // Mock biometric verification - integrate with actual biometric service
    // For testing, always return valid
    const confidence = Math.random() * 0.2 + 0.8; // 80-100% confidence
    const isValid = true; // Always valid for testing

    return {
      isValid,
      confidence,
      template: isValid ? `template_${Date.now()}` : null,
      reason: isValid ? 'Biometric verified successfully' : 'Biometric verification failed'
    };
  }

  compareBiometrics(template1, template2) {
    // Mock biometric comparison - return similarity score
    return Math.random() * 0.4 + 0.6; // 60-100% similarity
  }

  /**
   * Cleanup expired sessions
   */
  cleanupExpiredSessions() {
    const now = new Date();
    let cleanedCount = 0;

    for (const [sessionId, session] of this.verificationAttempts.entries()) {
      if (now > session.expiresAt) {
        this.verificationAttempts.delete(sessionId);
        cleanedCount++;
      }
    }

    // Cleanup expired OTPs
    for (const [otpKey, otpData] of this.otpStore.entries()) {
      if (now > otpData.expiresAt) {
        this.otpStore.delete(otpKey);
      }
    }

    if (cleanedCount > 0) {
      this.logger.info(`Cleaned up ${cleanedCount} expired MFA sessions`);
    }

    return cleanedCount;
  }

  /**
   * Get verification statistics
   */
  getVerificationStats() {
    const activeSessions = this.verificationAttempts.size;
    const activeOTPs = this.otpStore.size;
    const storedBiometrics = this.biometricData.size;

    const completedSessions = Array.from(this.verificationAttempts.values())
      .filter(session => session.status === 'completed').length;

    return {
      activeSessions,
      completedSessions,
      activeOTPs,
      storedBiometrics,
      successRate: activeSessions > 0 ? (completedSessions / activeSessions) * 100 : 0
    };
  }
}

module.exports = IdentityVerificationService;