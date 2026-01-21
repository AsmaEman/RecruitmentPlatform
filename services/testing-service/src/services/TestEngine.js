/**
 * Test engine for managing test execution and question randomization
 * Requirements: 4.1, 4.2
 */

const Question = require('../models/Question');
const Test = require('../models/Test');
const TestSession = require('../models/TestSession');

class TestEngine {
  constructor() {
    this.logger = require('../utils/logger');
  }

  /**
   * Create a new test session for a candidate
   */
  async createTestSession(testId, candidateId, candidateEmail, ipAddress, userAgent) {
    try {
      const test = await Test.findById(testId).populate('questions.questionId');
      if (!test || !test.isActive) {
        throw new Error('Test not found or inactive');
      }

      // Check if test is within allowed time window
      const now = new Date();
      if (test.startDate && now < test.startDate) {
        throw new Error('Test has not started yet');
      }
      if (test.endDate && now > test.endDate) {
        throw new Error('Test has expired');
      }

      // Check for existing session
      const existingSession = await TestSession.findOne({
        testId,
        candidateId,
        status: { $in: ['not_started', 'in_progress', 'paused'] }
      });

      if (existingSession) {
        return existingSession;
      }

      // Generate question order
      const questionsOrder = this.generateQuestionOrder(test);

      const session = new TestSession({
        testId,
        candidateId,
        candidateEmail,
        questionsOrder,
        timeRemaining: test.totalTimeLimit,
        maxScore: this.calculateMaxScore(test),
        ipAddress,
        userAgent
      });

      await session.save();
      this.logger.info(`Test session created for candidate ${candidateId}, test ${testId}`);

      return session;
    } catch (error) {
      this.logger.error(`Error creating test session: ${error.message}`);
      throw error;
    }
  }

  /**
   * Generate randomized question order if configured
   */
  generateQuestionOrder(test) {
    let questions = [...test.questions];

    if (test.randomizeQuestions) {
      questions = this.shuffleArray(questions);
    } else {
      // Sort by order field
      questions.sort((a, b) => a.order - b.order);
    }

    return questions.map(q => q.questionId._id);
  }

  /**
   * Get next question for a test session
   */
  async getNextQuestion(sessionId) {
    try {
      const session = await TestSession.findById(sessionId)
        .populate('testId')
        .populate({
          path: 'questionsOrder',
          model: 'Question'
        });

      if (!session) {
        throw new Error('Test session not found');
      }

      if (session.status !== 'in_progress' && session.status !== 'not_started') {
        throw new Error('Test session is not active');
      }

      // Start session if not started
      if (session.status === 'not_started') {
        session.status = 'in_progress';
        session.startedAt = new Date();
        await session.save();
      }

      // Check if test is completed
      if (session.currentQuestionIndex >= session.questionsOrder.length) {
        return null; // No more questions
      }

      const question = session.questionsOrder[session.currentQuestionIndex];

      // Prepare question for client (remove sensitive data)
      const clientQuestion = this.prepareQuestionForClient(question, session.testId);

      return {
        question: clientQuestion,
        questionIndex: session.currentQuestionIndex,
        totalQuestions: session.questionsOrder.length,
        timeRemaining: session.timeRemaining
      };
    } catch (error) {
      this.logger.error(`Error getting next question: ${error.message}`);
      throw error;
    }
  }

  /**
   * Submit answer for a question
   */
  async submitAnswer(sessionId, questionId, answer) {
    try {
      const session = await TestSession.findById(sessionId).populate('testId');
      if (!session) {
        throw new Error('Test session not found');
      }

      const question = await Question.findById(questionId);
      if (!question) {
        throw new Error('Question not found');
      }

      // Validate and score answer
      const { isCorrect, points } = this.scoreAnswer(question, answer);

      // Update or add answer
      const existingAnswerIndex = session.answers.findIndex(
        a => a.questionId.toString() === questionId.toString()
      );

      const answerData = {
        questionId,
        answer,
        isCorrect,
        points,
        submittedAt: new Date()
      };

      if (existingAnswerIndex >= 0) {
        session.answers[existingAnswerIndex] = answerData;
      } else {
        session.answers.push(answerData);
      }

      // Update session scores
      this.updateSessionScores(session);

      // Move to next question if not adaptive
      if (!session.testId.isAdaptive) {
        session.currentQuestionIndex++;
      }

      await session.save();

      return {
        isCorrect,
        points,
        totalScore: session.totalScore,
        percentage: session.percentage
      };
    } catch (error) {
      this.logger.error(`Error submitting answer: ${error.message}`);
      throw error;
    }
  }

  /**
   * Complete test session
   */
  async completeTestSession(sessionId) {
    try {
      const session = await TestSession.findById(sessionId);
      if (!session) {
        throw new Error('Test session not found');
      }

      session.status = 'completed';
      session.completedAt = new Date();

      // Final score calculation
      this.updateSessionScores(session);

      await session.save();

      this.logger.info(`Test session completed for candidate ${session.candidateId}`);

      return {
        totalScore: session.totalScore,
        maxScore: session.maxScore,
        percentage: session.percentage,
        completedAt: session.completedAt
      };
    } catch (error) {
      this.logger.error(`Error completing test session: ${error.message}`);
      throw error;
    }
  }

  /**
   * Auto-save session progress
   */
  async autoSaveProgress(sessionId, progressData) {
    try {
      const session = await TestSession.findById(sessionId);
      if (!session) {
        throw new Error('Test session not found');
      }

      session.autoSaveData = progressData;
      session.lastAutoSave = new Date();

      await session.save();

      return { success: true, timestamp: session.lastAutoSave };
    } catch (error) {
      this.logger.error(`Error auto-saving progress: ${error.message}`);
      throw error;
    }
  }

  /**
   * Score an answer based on question type
   */
  scoreAnswer(question, answer) {
    let isCorrect = false;
    let points = 0;

    switch (question.type) {
      case 'multiple_choice':
        const correctOptions = question.options.filter(opt => opt.isCorrect);
        if (Array.isArray(answer)) {
          // Multiple correct answers
          const correctIds = correctOptions.map(opt => opt._id.toString());
          const answerIds = answer.map(id => id.toString());
          isCorrect = correctIds.length === answerIds.length &&
            correctIds.every(id => answerIds.includes(id));
        } else {
          // Single correct answer
          const correctOption = correctOptions[0];
          isCorrect = correctOption && correctOption._id.toString() === answer.toString();
        }
        points = isCorrect ? question.points : 0;
        break;

      case 'true_false':
        const correctAnswer = question.options.find(opt => opt.isCorrect);
        isCorrect = correctAnswer && correctAnswer.text.toLowerCase() === answer.toString().toLowerCase();
        points = isCorrect ? question.points : 0;
        break;

      case 'coding':
        // Coding questions need separate evaluation
        // For now, return partial credit
        points = question.points * 0.5; // Placeholder
        isCorrect = false; // Will be determined by code execution
        break;

      case 'essay':
        // Essay questions need manual grading
        points = 0;
        isCorrect = false;
        break;

      default:
        points = 0;
        isCorrect = false;
    }

    return { isCorrect, points };
  }

  /**
   * Update session total scores
   */
  updateSessionScores(session) {
    session.totalScore = session.answers.reduce((sum, answer) => sum + (answer.points || 0), 0);
    session.percentage = session.maxScore > 0 ? (session.totalScore / session.maxScore) * 100 : 0;
  }

  /**
   * Calculate maximum possible score for a test
   */
  calculateMaxScore(test) {
    return test.questions.reduce((sum, q) => sum + (q.points || q.questionId.points || 1), 0);
  }

  /**
   * Prepare question for client (remove answers and sensitive data)
   */
  prepareQuestionForClient(question, test) {
    const clientQuestion = {
      _id: question._id,
      title: question.title,
      description: question.description,
      type: question.type,
      points: question.points,
      language: question.language,
      starterCode: question.starterCode,
      timeLimit: question.timeLimit
    };

    // Add options for multiple choice (without correct answers)
    if (question.type === 'multiple_choice' || question.type === 'true_false') {
      clientQuestion.options = question.options.map(opt => ({
        _id: opt._id,
        text: opt.text
      }));

      // Randomize options if configured
      if (test.randomizeOptions) {
        clientQuestion.options = this.shuffleArray(clientQuestion.options);
      }
    }

    // Add public test cases for coding questions
    if (question.type === 'coding') {
      clientQuestion.testCases = question.testCases
        .filter(tc => !tc.isHidden)
        .map(tc => ({
          input: tc.input,
          expectedOutput: tc.expectedOutput
        }));
    }

    return clientQuestion;
  }

  /**
   * Utility function to shuffle array
   */
  shuffleArray(array) {
    const shuffled = [...array];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  }
}

module.exports = TestEngine;