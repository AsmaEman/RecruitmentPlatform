/**
 * Property test for auto-save persistence
 * Property 3: Auto-save Persistence
 * Validates: Requirements 4.5
 */

const SessionManager = require('../services/SessionManager');
const mongoose = require('mongoose');

describe('Property Test: Auto-save Persistence', () => {
  let sessionManager;
  let testSessionId;

  beforeAll(async () => {
    // Connect to test database
    if (mongoose.connection.readyState === 0) {
      await mongoose.connect(process.env.MONGODB_TEST_URL || 'mongodb://localhost:27017/recruitment_test');
    }

    sessionManager = new SessionManager();
    await sessionManager.initialize();
  });

  afterAll(async () => {
    await sessionManager.shutdown();
    if (mongoose.connection.readyState !== 0) {
      await mongoose.connection.close();
    }
  });

  beforeEach(async () => {
    // Create a test session
    const result = await sessionManager.createSession(
      'test-candidate-123',
      'test-test-456',
      {
        timeLimit: 3600000, // 1 hour
        autoSaveEnabled: true
      }
    );
    expect(result.success).toBe(true);
    testSessionId = result.sessionId;
  });

  afterEach(async () => {
    // Clean up test session
    if (testSessionId) {
      await sessionManager.endSession(testSessionId, 'test-cleanup');
      testSessionId = null;
    }
  });

  /**
   * Property: All session data must persist across auto-saves
   * Invariant: Data written before auto-save equals data read after auto-save
   */
  describe('Data Persistence Property', () => {
    test('should persist answers across auto-saves', async () => {
      const testAnswers = {
        'q1': { answer: 'Answer 1', timestamp: new Date() },
        'q2': { answer: 'Answer 2', timestamp: new Date() },
        'q3': { answer: 'Multiple choice A', timestamp: new Date() }
      };

      // Submit answers
      for (const [questionId, answerData] of Object.entries(testAnswers)) {
        const result = await sessionManager.submitAnswer(testSessionId, questionId, answerData.answer);
        expect(result.success).toBe(true);
      }

      // Trigger auto-save
      const autoSaveResult = await sessionManager.autoSave(testSessionId, {});
      expect(autoSaveResult.success).toBe(true);

      // Retrieve session and verify answers persist
      const sessionResult = await sessionManager.getSession(testSessionId);
      expect(sessionResult.success).toBe(true);

      const session = sessionResult.session;
      expect(session.answers).toBeDefined();

      // Property: All submitted answers must be present
      for (const questionId of Object.keys(testAnswers)) {
        expect(session.answers[questionId]).toBeDefined();
        expect(session.answers[questionId].answer).toBe(testAnswers[questionId].answer);
        expect(session.answers[questionId].questionId).toBe(questionId);
      }
    });

    test('should persist code submissions across auto-saves', async () => {
      const testCodeSubmissions = {
        'coding-q1': {
          code: 'def hello():\n    return "Hello World"',
          language: 'python'
        },
        'coding-q2': {
          code: 'function fibonacci(n) {\n    return n <= 1 ? n : fibonacci(n-1) + fibonacci(n-2);\n}',
          language: 'javascript'
        }
      };

      // Submit code
      for (const [questionId, codeData] of Object.entries(testCodeSubmissions)) {
        const result = await sessionManager.submitCode(
          testSessionId,
          questionId,
          codeData.code,
          codeData.language
        );
        expect(result.success).toBe(true);
      }

      // Trigger auto-save
      const autoSaveResult = await sessionManager.autoSave(testSessionId, {});
      expect(autoSaveResult.success).toBe(true);

      // Retrieve session and verify code submissions persist
      const sessionResult = await sessionManager.getSession(testSessionId);
      expect(sessionResult.success).toBe(true);

      const session = sessionResult.session;
      expect(session.codeSubmissions).toBeDefined();

      // Property: All code submissions must be present and unchanged
      for (const [questionId, expectedCode] of Object.entries(testCodeSubmissions)) {
        expect(session.codeSubmissions[questionId]).toBeDefined();
        expect(session.codeSubmissions[questionId].code).toBe(expectedCode.code);
        expect(session.codeSubmissions[questionId].language).toBe(expectedCode.language);
        expect(session.codeSubmissions[questionId].questionId).toBe(questionId);
      }
    });

    test('should persist violations across auto-saves', async () => {
      const testViolations = [
        {
          type: 'tab_switch',
          message: 'User switched tabs',
          severity: 'medium'
        },
        {
          type: 'fullscreen_exit',
          message: 'User exited fullscreen',
          severity: 'high'
        },
        {
          type: 'right_click',
          message: 'User attempted right-click',
          severity: 'low'
        }
      ];

      // Record violations
      for (const violation of testViolations) {
        const result = await sessionManager.recordViolation(testSessionId, violation);
        expect(result.success).toBe(true);
      }

      // Trigger auto-save
      const autoSaveResult = await sessionManager.autoSave(testSessionId, {});
      expect(autoSaveResult.success).toBe(true);

      // Retrieve session and verify violations persist
      const sessionResult = await sessionManager.getSession(testSessionId);
      expect(sessionResult.success).toBe(true);

      const session = sessionResult.session;
      expect(session.violations).toBeDefined();
      expect(session.violations.length).toBe(testViolations.length);

      // Property: All violations must be present with timestamps
      testViolations.forEach((expectedViolation, index) => {
        const actualViolation = session.violations[index];
        expect(actualViolation.type).toBe(expectedViolation.type);
        expect(actualViolation.message).toBe(expectedViolation.message);
        expect(actualViolation.severity).toBe(expectedViolation.severity);
        expect(actualViolation.timestamp).toBeDefined();
      });
    });
  });

  /**
   * Property: Auto-save must occur within specified intervals
   * Invariant: lastAutoSave timestamp must be updated within interval + tolerance
   */
  describe('Auto-save Timing Property', () => {
    test('should auto-save within specified interval', async () => {
      const shortInterval = 2000; // 2 seconds for testing
      sessionManager.autoSaveInterval = shortInterval;

      // Start auto-save
      sessionManager.startAutoSave(testSessionId);

      // Submit some data to trigger save need
      await sessionManager.submitAnswer(testSessionId, 'test-q', 'test-answer');

      // Wait for auto-save interval + tolerance
      await new Promise(resolve => setTimeout(resolve, shortInterval + 1000));

      // Check that auto-save occurred
      const sessionResult = await sessionManager.getSession(testSessionId);
      expect(sessionResult.success).toBe(true);

      const session = sessionResult.session;
      const lastAutoSave = new Date(session.lastAutoSave);
      const now = new Date();

      // Property: Auto-save should have occurred recently
      const timeSinceAutoSave = now.getTime() - lastAutoSave.getTime();
      expect(timeSinceAutoSave).toBeLessThan(shortInterval + 500); // 500ms tolerance

      // Stop auto-save
      sessionManager.stopAutoSave(testSessionId);
    }, 10000);

    test('should update lastAutoSave timestamp on manual auto-save', async () => {
      // Get initial timestamp
      const initialResult = await sessionManager.getSession(testSessionId);
      expect(initialResult.success).toBe(true);
      const initialTimestamp = new Date(initialResult.session.lastAutoSave);

      // Wait a moment
      await new Promise(resolve => setTimeout(resolve, 100));

      // Trigger manual auto-save
      const autoSaveResult = await sessionManager.autoSave(testSessionId, {
        currentQuestionIndex: 5
      });
      expect(autoSaveResult.success).toBe(true);

      // Check timestamp was updated
      const updatedResult = await sessionManager.getSession(testSessionId);
      expect(updatedResult.success).toBe(true);
      const updatedTimestamp = new Date(updatedResult.session.lastAutoSave);

      // Property: lastAutoSave must be updated
      expect(updatedTimestamp.getTime()).toBeGreaterThan(initialTimestamp.getTime());
      expect(updatedResult.session.currentQuestionIndex).toBe(5);
    });
  });

  /**
   * Property: Session recovery must restore exact state
   * Invariant: Recovered session state equals pre-interruption state
   */
  describe('Session Recovery Property', () => {
    test('should recover complete session state after interruption', async () => {
      // Create comprehensive session state
      const testData = {
        answers: {
          'q1': 'Answer 1',
          'q2': 'Answer 2',
          'q3': 'Answer 3'
        },
        codeSubmissions: {
          'coding-q1': {
            code: 'print("Hello World")',
            language: 'python'
          }
        },
        violations: [
          {
            type: 'test_violation',
            message: 'Test violation message'
          }
        ],
        currentQuestionIndex: 3
      };

      // Submit all test data
      for (const [questionId, answer] of Object.entries(testData.answers)) {
        await sessionManager.submitAnswer(testSessionId, questionId, answer);
      }

      for (const [questionId, codeData] of Object.entries(testData.codeSubmissions)) {
        await sessionManager.submitCode(testSessionId, questionId, codeData.code, codeData.language);
      }

      for (const violation of testData.violations) {
        await sessionManager.recordViolation(testSessionId, violation);
      }

      await sessionManager.updateSession(testSessionId, {
        currentQuestionIndex: testData.currentQuestionIndex
      });

      // Trigger auto-save to persist state
      const autoSaveResult = await sessionManager.autoSave(testSessionId, {});
      expect(autoSaveResult.success).toBe(true);

      // Simulate session recovery
      const recoveryResult = await sessionManager.resumeSession(testSessionId);
      expect(recoveryResult.success).toBe(true);

      const recoveredSession = recoveryResult.session;

      // Property: All data must be recovered exactly
      expect(recoveredSession.currentQuestionIndex).toBe(testData.currentQuestionIndex);

      // Check answers
      for (const [questionId, expectedAnswer] of Object.entries(testData.answers)) {
        expect(recoveredSession.answers[questionId]).toBeDefined();
        expect(recoveredSession.answers[questionId].answer).toBe(expectedAnswer);
      }

      // Check code submissions
      for (const [questionId, expectedCode] of Object.entries(testData.codeSubmissions)) {
        expect(recoveredSession.codeSubmissions[questionId]).toBeDefined();
        expect(recoveredSession.codeSubmissions[questionId].code).toBe(expectedCode.code);
        expect(recoveredSession.codeSubmissions[questionId].language).toBe(expectedCode.language);
      }
    });

    test('should handle recovery of expired sessions', async () => {
      // Create session with very short time limit
      const shortSessionResult = await sessionManager.createSession(
        'test-candidate-expired',
        'test-test-expired',
        {
          timeLimit: 100, // 100ms - very short
          autoSaveEnabled: true
        }
      );
      expect(shortSessionResult.success).toBe(true);
      const shortSessionId = shortSessionResult.sessionId;

      // Wait for session to expire
      await new Promise(resolve => setTimeout(resolve, 200));

      // Attempt recovery
      const recoveryResult = await sessionManager.resumeSession(shortSessionId);

      // Property: Expired sessions should not be recoverable
      expect(recoveryResult.success).toBe(false);
      expect(recoveryResult.error).toContain('expired');

      // Verify session was marked as completed
      const sessionResult = await sessionManager.getSession(shortSessionId);
      expect(sessionResult.success).toBe(true);
      expect(sessionResult.session.status).toBe('completed');
      expect(sessionResult.session.endReason).toBe('expired');
    });
  });

  /**
   * Property: Concurrent auto-saves must maintain data consistency
   * Invariant: No data corruption during concurrent operations
   */
  describe('Concurrency Safety Property', () => {
    test('should handle concurrent auto-saves without data corruption', async () => {
      const concurrentOperations = [];

      // Create multiple concurrent operations
      for (let i = 0; i < 10; i++) {
        concurrentOperations.push(
          sessionManager.submitAnswer(testSessionId, `q${i}`, `Answer ${i}`)
        );
        concurrentOperations.push(
          sessionManager.autoSave(testSessionId, { currentQuestionIndex: i })
        );
      }

      // Execute all operations concurrently
      const results = await Promise.all(concurrentOperations);

      // Property: All operations should succeed
      results.forEach(result => {
        expect(result.success).toBe(true);
      });

      // Verify final state is consistent
      const finalResult = await sessionManager.getSession(testSessionId);
      expect(finalResult.success).toBe(true);

      const session = finalResult.session;

      // Property: All answers should be present
      expect(Object.keys(session.answers).length).toBe(10);
      for (let i = 0; i < 10; i++) {
        expect(session.answers[`q${i}`]).toBeDefined();
        expect(session.answers[`q${i}`].answer).toBe(`Answer ${i}`);
      }
    });

    test('should maintain data integrity during rapid updates', async () => {
      const rapidUpdates = [];
      const questionId = 'rapid-update-q';

      // Create rapid sequential updates
      for (let i = 0; i < 20; i++) {
        rapidUpdates.push(
          sessionManager.submitAnswer(testSessionId, questionId, `Rapid Answer ${i}`)
            .then(() => sessionManager.autoSave(testSessionId, {}))
        );
      }

      await Promise.all(rapidUpdates);

      // Verify final state
      const sessionResult = await sessionManager.getSession(testSessionId);
      expect(sessionResult.success).toBe(true);

      const session = sessionResult.session;

      // Property: Final answer should be one of the submitted answers
      expect(session.answers[questionId]).toBeDefined();
      expect(session.answers[questionId].answer).toMatch(/^Rapid Answer \d+$/);

      // Property: Only one answer should exist for the question
      const answerKeys = Object.keys(session.answers).filter(key => key === questionId);
      expect(answerKeys.length).toBe(1);
    });
  });

  /**
   * Property: Auto-save must be atomic
   * Invariant: Either all data is saved or none is saved (no partial saves)
   */
  describe('Atomicity Property', () => {
    test('should save all session data atomically', async () => {
      const complexUpdate = {
        currentQuestionIndex: 10,
        answers: {
          'atomic-q1': { answer: 'Atomic Answer 1', timestamp: new Date() },
          'atomic-q2': { answer: 'Atomic Answer 2', timestamp: new Date() }
        },
        codeSubmissions: {
          'atomic-coding-q1': {
            code: 'def atomic_function(): return "atomic"',
            language: 'python',
            timestamp: new Date()
          }
        }
      };

      // Perform atomic auto-save
      const autoSaveResult = await sessionManager.autoSave(testSessionId, complexUpdate);
      expect(autoSaveResult.success).toBe(true);

      // Verify all data was saved together
      const sessionResult = await sessionManager.getSession(testSessionId);
      expect(sessionResult.success).toBe(true);

      const session = sessionResult.session;

      // Property: All parts of the update must be present
      expect(session.currentQuestionIndex).toBe(complexUpdate.currentQuestionIndex);

      for (const [questionId, answerData] of Object.entries(complexUpdate.answers)) {
        expect(session.answers[questionId]).toBeDefined();
        expect(session.answers[questionId].answer).toBe(answerData.answer);
      }

      for (const [questionId, codeData] of Object.entries(complexUpdate.codeSubmissions)) {
        expect(session.codeSubmissions[questionId]).toBeDefined();
        expect(session.codeSubmissions[questionId].code).toBe(codeData.code);
        expect(session.codeSubmissions[questionId].language).toBe(codeData.language);
      }
    });
  });
});