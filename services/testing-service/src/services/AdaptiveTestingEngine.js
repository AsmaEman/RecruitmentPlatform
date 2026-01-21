/**
 * Adaptive testing algorithm implementation
 * Requirements: 4.7
 */

class AdaptiveTestingEngine {
  constructor(options = {}) {
    this.options = {
      initialDifficulty: 0.5,
      difficultyAdjustmentFactor: 0.3,
      minDifficulty: 0.1,
      maxDifficulty: 0.9,
      confidenceThreshold: 0.8,
      maxQuestions: 50,
      minQuestions: 10,
      ...options
    };

    this.logger = require('../utils/logger');
  }

  /**
   * Initialize adaptive test session
   */
  initializeAdaptiveTest(candidateId, testConfig) {
    const adaptiveState = {
      candidateId,
      testConfig,
      currentDifficulty: this.options.initialDifficulty,
      abilityEstimate: this.options.initialDifficulty,
      confidenceLevel: 0,
      questionsAnswered: 0,
      correctAnswers: 0,
      questionHistory: [],
      difficultyHistory: [this.options.initialDifficulty],
      abilityHistory: [this.options.initialDifficulty],
      isComplete: false,
      startTime: new Date()
    };

    return { success: true, adaptiveState };
  }

  /**
   * Select next question based on current ability estimate
   */
  selectNextQuestion(adaptiveState, availableQuestions) {
    try {
      if (adaptiveState.isComplete) {
        return { success: false, error: 'Test is already complete' };
      }

      const answeredQuestionIds = adaptiveState.questionHistory.map(q => q.questionId);
      const unansweredQuestions = availableQuestions.filter(
        q => !answeredQuestionIds.includes(q.id)
      );

      if (unansweredQuestions.length === 0) {
        return { success: false, error: 'No more questions available' };
      }

      const targetDifficulty = adaptiveState.currentDifficulty;
      let bestQuestion = null;
      let smallestDifference = Infinity;

      unansweredQuestions.forEach(question => {
        const difficultyDifference = Math.abs(question.difficulty - targetDifficulty);

        const recentlyUsed = adaptiveState.questionHistory
          .slice(-5)
          .some(q => q.questionId === question.id);

        const adjustedDifference = recentlyUsed ? difficultyDifference + 0.2 : difficultyDifference;

        if (adjustedDifference < smallestDifference) {
          smallestDifference = adjustedDifference;
          bestQuestion = question;
        }
      });

      if (!bestQuestion) {
        return { success: false, error: 'No suitable question found' };
      }

      return {
        success: true,
        question: bestQuestion,
        reasoning: {
          targetDifficulty,
          selectedDifficulty: bestQuestion.difficulty,
          difference: smallestDifference
        }
      };

    } catch (error) {
      this.logger.error(`Question selection error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Process answer and update ability estimate
   */
  processAnswer(adaptiveState, questionId, isCorrect, responseTime, question) {
    try {
      const now = new Date();

      const answerRecord = {
        questionId,
        isCorrect,
        responseTime,
        difficulty: question.difficulty,
        timestamp: now,
        abilityBeforeAnswer: adaptiveState.abilityEstimate,
        difficultyBeforeAnswer: adaptiveState.currentDifficulty
      };

      adaptiveState.questionHistory.push(answerRecord);
      adaptiveState.questionsAnswered++;

      if (isCorrect) {
        adaptiveState.correctAnswers++;
      }

      const newAbilityEstimate = this.updateAbilityEstimate(
        adaptiveState.abilityEstimate,
        question.difficulty,
        isCorrect,
        responseTime
      );

      adaptiveState.abilityEstimate = newAbilityEstimate;
      adaptiveState.abilityHistory.push(newAbilityEstimate);

      const newDifficulty = this.calculateNextDifficulty(
        adaptiveState.abilityEstimate,
        adaptiveState.confidenceLevel,
        isCorrect
      );

      adaptiveState.currentDifficulty = Math.max(
        this.options.minDifficulty,
        Math.min(this.options.maxDifficulty, newDifficulty)
      );

      adaptiveState.difficultyHistory.push(adaptiveState.currentDifficulty);
      adaptiveState.confidenceLevel = this.calculateConfidenceLevel(adaptiveState);
      adaptiveState.isComplete = this.shouldCompleteTest(adaptiveState);

      return {
        success: true,
        adaptiveState,
        updates: {
          newAbilityEstimate,
          newDifficulty: adaptiveState.currentDifficulty,
          confidenceLevel: adaptiveState.confidenceLevel,
          isComplete: adaptiveState.isComplete
        }
      };

    } catch (error) {
      this.logger.error(`Answer processing error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  updateAbilityEstimate(currentAbility, questionDifficulty, isCorrect, responseTime) {
    const expectedProbability = 1 / (1 + Math.exp(-(currentAbility - questionDifficulty)));
    const actualResult = isCorrect ? 1 : 0;
    const surprise = Math.abs(actualResult - expectedProbability);

    let abilityAdjustment = surprise * this.options.difficultyAdjustmentFactor;

    if (isCorrect) {
      abilityAdjustment = abilityAdjustment;
    } else {
      abilityAdjustment = -abilityAdjustment;
    }

    const timeAdjustment = this.calculateTimeAdjustment(responseTime, questionDifficulty);
    abilityAdjustment += timeAdjustment;

    const newAbility = currentAbility + abilityAdjustment;
    return Math.max(0.05, Math.min(0.95, newAbility));
  }

  calculateTimeAdjustment(responseTime, questionDifficulty) {
    const expectedTime = 30000 + (questionDifficulty * 60000);
    const timeRatio = responseTime / expectedTime;

    if (timeRatio < 0.5) {
      return 0.05;
    } else if (timeRatio > 2.0) {
      return -0.05;
    }

    return 0;
  }

  calculateNextDifficulty(abilityEstimate, confidenceLevel, wasLastCorrect) {
    let nextDifficulty = abilityEstimate;

    if (confidenceLevel < 0.5) {
      const exploration = (Math.random() - 0.5) * 0.2;
      nextDifficulty += exploration;
    } else {
      const fineTuning = (Math.random() - 0.5) * 0.1;
      nextDifficulty += fineTuning;
    }

    if (wasLastCorrect) {
      nextDifficulty += 0.05;
    } else {
      nextDifficulty -= 0.05;
    }

    return nextDifficulty;
  }

  calculateConfidenceLevel(adaptiveState) {
    if (adaptiveState.questionsAnswered < 3) {
      return 0;
    }

    const recentAnswers = adaptiveState.questionHistory.slice(-5);
    const recentCorrectRate = recentAnswers.filter(a => a.isCorrect).length / recentAnswers.length;

    const recentAbilities = adaptiveState.abilityHistory.slice(-5);
    const abilityVariance = this.calculateVariance(recentAbilities);
    const stabilityScore = Math.max(0, 1 - (abilityVariance * 10));

    const difficultyMatches = recentAnswers.map(answer => {
      const expectedProbability = 1 / (1 + Math.exp(-(answer.abilityBeforeAnswer - answer.difficulty)));
      const actualResult = answer.isCorrect ? 1 : 0;
      return 1 - Math.abs(actualResult - expectedProbability);
    });

    const averageMatch = difficultyMatches.reduce((sum, match) => sum + match, 0) / difficultyMatches.length;
    const confidence = (stabilityScore * 0.4) + (averageMatch * 0.4) + (Math.min(recentCorrectRate, 1 - recentCorrectRate) * 0.2);

    return Math.max(0, Math.min(1, confidence));
  }

  calculateVariance(numbers) {
    if (numbers.length < 2) return 0;

    const mean = numbers.reduce((sum, num) => sum + num, 0) / numbers.length;
    const squaredDifferences = numbers.map(num => Math.pow(num - mean, 2));
    const variance = squaredDifferences.reduce((sum, diff) => sum + diff, 0) / numbers.length;

    return variance;
  }

  shouldCompleteTest(adaptiveState) {
    if (adaptiveState.questionsAnswered < this.options.minQuestions) {
      return false;
    }

    if (adaptiveState.questionsAnswered >= this.options.maxQuestions) {
      return true;
    }

    if (adaptiveState.confidenceLevel >= this.options.confidenceThreshold) {
      return true;
    }

    if (adaptiveState.abilityHistory.length >= 10) {
      const recentAbilities = adaptiveState.abilityHistory.slice(-5);
      const variance = this.calculateVariance(recentAbilities);

      if (variance < 0.01) {
        return true;
      }
    }

    return false;
  }

  generateResults(adaptiveState) {
    try {
      const endTime = new Date();
      const totalTime = endTime.getTime() - adaptiveState.startTime.getTime();

      const results = {
        candidateId: adaptiveState.candidateId,
        finalAbilityEstimate: adaptiveState.abilityEstimate,
        confidenceLevel: adaptiveState.confidenceLevel,
        questionsAnswered: adaptiveState.questionsAnswered,
        correctAnswers: adaptiveState.correctAnswers,
        accuracyRate: adaptiveState.correctAnswers / adaptiveState.questionsAnswered,
        totalTime,
        averageResponseTime: this.calculateAverageResponseTime(adaptiveState),
        difficultyProgression: adaptiveState.difficultyHistory,
        abilityProgression: adaptiveState.abilityHistory,
        performanceAnalysis: this.analyzePerformance(adaptiveState),
        completionReason: this.getCompletionReason(adaptiveState)
      };

      return { success: true, results };

    } catch (error) {
      this.logger.error(`Results generation error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  calculateAverageResponseTime(adaptiveState) {
    if (adaptiveState.questionHistory.length === 0) return 0;

    const totalTime = adaptiveState.questionHistory.reduce(
      (sum, answer) => sum + (answer.responseTime || 0),
      0
    );

    return totalTime / adaptiveState.questionHistory.length;
  }

  analyzePerformance(adaptiveState) {
    const analysis = {
      consistencyScore: 0,
      improvementTrend: 'stable',
      strengthAreas: [],
      weaknessAreas: [],
      responseTimePattern: 'normal'
    };

    if (adaptiveState.questionHistory.length < 5) {
      return analysis;
    }

    const correctnessPattern = adaptiveState.questionHistory.map(q => q.isCorrect ? 1 : 0);
    const consistency = 1 - this.calculateVariance(correctnessPattern);
    analysis.consistencyScore = Math.max(0, Math.min(1, consistency));

    const firstHalf = adaptiveState.abilityHistory.slice(0, Math.floor(adaptiveState.abilityHistory.length / 2));
    const secondHalf = adaptiveState.abilityHistory.slice(Math.floor(adaptiveState.abilityHistory.length / 2));

    const firstHalfAvg = firstHalf.reduce((sum, ability) => sum + ability, 0) / firstHalf.length;
    const secondHalfAvg = secondHalf.reduce((sum, ability) => sum + ability, 0) / secondHalf.length;

    if (secondHalfAvg > firstHalfAvg + 0.05) {
      analysis.improvementTrend = 'improving';
    } else if (secondHalfAvg < firstHalfAvg - 0.05) {
      analysis.improvementTrend = 'declining';
    }

    const responseTimes = adaptiveState.questionHistory.map(q => q.responseTime);
    const avgResponseTime = responseTimes.reduce((sum, time) => sum + time, 0) / responseTimes.length;
    const responseTimeVariance = this.calculateVariance(responseTimes);

    if (avgResponseTime < 20000) {
      analysis.responseTimePattern = 'fast';
    } else if (avgResponseTime > 60000) {
      analysis.responseTimePattern = 'slow';
    } else if (responseTimeVariance > 1000000000) {
      analysis.responseTimePattern = 'inconsistent';
    }

    return analysis;
  }

  getCompletionReason(adaptiveState) {
    if (adaptiveState.questionsAnswered >= this.options.maxQuestions) {
      return 'maximum_questions_reached';
    }

    if (adaptiveState.confidenceLevel >= this.options.confidenceThreshold) {
      return 'confidence_threshold_reached';
    }

    if (adaptiveState.abilityHistory.length >= 10) {
      const recentAbilities = adaptiveState.abilityHistory.slice(-5);
      const variance = this.calculateVariance(recentAbilities);

      if (variance < 0.01) {
        return 'ability_stabilized';
      }
    }

    return 'manual_completion';
  }

  getAdaptiveStats(adaptiveState) {
    return {
      questionsAnswered: adaptiveState.questionsAnswered,
      currentDifficulty: adaptiveState.currentDifficulty,
      abilityEstimate: adaptiveState.abilityEstimate,
      confidenceLevel: adaptiveState.confidenceLevel,
      accuracyRate: adaptiveState.correctAnswers / Math.max(1, adaptiveState.questionsAnswered),
      isComplete: adaptiveState.isComplete,
      estimatedQuestionsRemaining: this.estimateQuestionsRemaining(adaptiveState)
    };
  }

  estimateQuestionsRemaining(adaptiveState) {
    if (adaptiveState.isComplete) {
      return 0;
    }

    const questionsToMinimum = Math.max(0, this.options.minQuestions - adaptiveState.questionsAnswered);

    if (questionsToMinimum > 0) {
      return questionsToMinimum;
    }

    const confidenceGap = this.options.confidenceThreshold - adaptiveState.confidenceLevel;
    const estimatedQuestions = Math.ceil(confidenceGap * 20);

    return Math.min(estimatedQuestions, this.options.maxQuestions - adaptiveState.questionsAnswered);
  }
}

module.exports = AdaptiveTestingEngine;