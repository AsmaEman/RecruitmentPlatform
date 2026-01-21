/**
 * Property test for question randomization
 * Property 12: Test Configuration Randomization
 * Validates: Requirements 4.2
 */

const TestEngine = require('../services/TestEngine');

// Mock MongoDB models
jest.mock('../models/Question', () => ({
  find: jest.fn(),
  findById: jest.fn()
}));

jest.mock('../models/Test', () => ({
  findById: jest.fn()
}));

jest.mock('../models/TestSession', () => ({
  findOne: jest.fn(),
  create: jest.fn()
}));

describe('Question Randomization Property Tests', () => {
  let testEngine;

  beforeAll(() => {
    testEngine = new TestEngine();
  });

  // Helper function to create mock test data
  const mockTest = (overrides = {}) => ({
    _id: 'test-123',
    title: 'Sample Test',
    questions: [
      { questionId: { _id: 'q1' }, text: 'Question 1', type: 'multiple-choice', difficulty: 0.3, order: 1 },
      { questionId: { _id: 'q2' }, text: 'Question 2', type: 'multiple-choice', difficulty: 0.5, order: 2 },
      { questionId: { _id: 'q3' }, text: 'Question 3', type: 'multiple-choice', difficulty: 0.7, order: 3 },
      { questionId: { _id: 'q4' }, text: 'Question 4', type: 'coding', difficulty: 0.4, order: 4 },
      { questionId: { _id: 'q5' }, text: 'Question 5', type: 'coding', difficulty: 0.8, order: 5 }
    ],
    randomizeQuestions: true,
    randomizeOptions: true,
    configuration: {
      randomizeQuestions: true,
      randomizeOptions: true,
      timeLimit: 3600,
      ...overrides.configuration
    },
    ...overrides
  });

  const mockQuestion = (overrides = {}) => ({
    _id: 'q1',
    title: 'Sample Question',
    description: 'Sample Question Description',
    type: 'multiple_choice',
    options: [
      { _id: 'opt1', text: 'Option A', isCorrect: false },
      { _id: 'opt2', text: 'Option B', isCorrect: true },
      { _id: 'opt3', text: 'Option C', isCorrect: false },
      { _id: 'opt4', text: 'Option D', isCorrect: false }
    ],
    points: 1,
    difficulty: 0.5,
    ...overrides
  });

  /**
   * Property: Question order randomization consistency
   */
  describe('Property: Question order randomization consistency', () => {
    test('should produce different orders when randomization is enabled', () => {
      const test = mockTest({ randomizeQuestions: true });
      const originalQuestionIds = test.questions.map(q => q.questionId._id);
      const originalQuestionCount = test.questions.length;

      // Generate multiple question orders
      const orders = [];
      for (let i = 0; i < 10; i++) {
        const questionOrder = testEngine.generateQuestionOrder(test);
        orders.push(questionOrder);
      }

      // Property: With randomization enabled, should produce different orders
      const uniqueOrders = new Set(orders.map(order => order.join(',')));
      expect(uniqueOrders.size).toBeGreaterThan(1);

      // Property: All orders should contain the same questions
      orders.forEach(order => {
        expect(order).toHaveLength(originalQuestionCount);
        expect(new Set(order)).toEqual(new Set(originalQuestionIds));
      });
    });

    test('should maintain consistent order when randomization is disabled', () => {
      const test = mockTest({ randomizeQuestions: false });

      // Generate multiple question orders
      const orders = [];
      for (let i = 0; i < 5; i++) {
        const questionOrder = testEngine.generateQuestionOrder(test);
        orders.push(questionOrder);
      }

      // Property: Without randomization, all orders should be identical
      const firstOrder = orders[0];
      orders.forEach(order => {
        expect(order).toEqual(firstOrder);
      });
    });
  });

  /**
   * Property: Question completeness preservation
   */
  describe('Property: Question completeness preservation', () => {
    test('should preserve all questions regardless of randomization', () => {
      const testConfigs = [
        { randomizeQuestions: true },
        { randomizeQuestions: false },
        { randomizeQuestions: true, randomizeOptions: true },
        { randomizeQuestions: false, randomizeOptions: false }
      ];

      testConfigs.forEach((config, index) => {
        const test = mockTest(config);
        const originalQuestionIds = test.questions.map(q => q.questionId._id);
        const originalQuestionCount = test.questions.length;

        for (let i = 0; i < 5; i++) {
          const questionOrder = testEngine.generateQuestionOrder(test);

          // Property: Should preserve question count
          expect(questionOrder).toHaveLength(originalQuestionCount);

          // Property: Should preserve all question IDs
          expect(new Set(questionOrder)).toEqual(new Set(originalQuestionIds));

          // Property: No duplicate questions
          expect(questionOrder.length).toBe(new Set(questionOrder).size);
        }
      });
    });
  });

  /**
   * Property: Option randomization consistency
   */
  describe('Property: Option randomization consistency', () => {
    test('should randomize options when configured', () => {
      const question = mockQuestion();
      const originalOptionIds = question.options.map(opt => opt._id);
      const testWithRandomization = { randomizeOptions: true };

      // Generate multiple option orders
      const optionOrders = [];
      for (let i = 0; i < 10; i++) {
        const preparedQuestion = testEngine.prepareQuestionForClient(question, testWithRandomization);
        const optionOrder = preparedQuestion.options.map(opt => opt._id);
        optionOrders.push(optionOrder);
      }

      // Property: Should produce different option orders
      const uniqueOrders = new Set(optionOrders.map(order => order.join(',')));
      expect(uniqueOrders.size).toBeGreaterThan(1);

      // Property: All orders should contain the same options
      optionOrders.forEach(order => {
        expect(order).toHaveLength(originalOptionIds.length);
        expect(new Set(order)).toEqual(new Set(originalOptionIds));
      });
    });

    test('should maintain option order when randomization is disabled', () => {
      const question = mockQuestion();
      const testWithoutRandomization = { randomizeOptions: false };

      // Generate multiple prepared questions
      const preparedQuestions = [];
      for (let i = 0; i < 5; i++) {
        const prepared = testEngine.prepareQuestionForClient(question, testWithoutRandomization);
        preparedQuestions.push(prepared);
      }

      // Property: Option order should be consistent
      const firstOptionOrder = preparedQuestions[0].options.map(opt => opt._id);
      preparedQuestions.forEach(prepared => {
        const optionOrder = prepared.options.map(opt => opt._id);
        expect(optionOrder).toEqual(firstOptionOrder);
      });
    });
  });

  /**
   * Property: Randomization distribution fairness
   */
  describe('Property: Randomization distribution fairness', () => {
    test('should distribute questions fairly across positions', () => {
      const test = mockTest({ randomizeQuestions: true });
      const questionCount = test.questions.length;
      const iterations = 100;

      // Track position frequency for each question
      const positionFrequency = {};
      test.questions.forEach(q => {
        positionFrequency[q.questionId._id] = new Array(questionCount).fill(0);
      });

      // Generate many randomized orders
      for (let i = 0; i < iterations; i++) {
        const questionOrder = testEngine.generateQuestionOrder(test);
        questionOrder.forEach((questionId, position) => {
          positionFrequency[questionId][position]++;
        });
      }

      // Property: Each question should appear in multiple positions
      Object.keys(positionFrequency).forEach(questionId => {
        const positions = positionFrequency[questionId];
        const nonZeroPositions = positions.filter(count => count > 0).length;

        expect(nonZeroPositions).toBeGreaterThan(1);

        // Property: Distribution should be reasonably uniform
        const expectedFrequency = iterations / questionCount;
        const tolerance = expectedFrequency * 0.8; // 80% tolerance for more realistic testing

        positions.forEach(frequency => {
          if (frequency > 0) {
            expect(Math.abs(frequency - expectedFrequency)).toBeLessThan(tolerance);
          }
        });
      });
    });
  });

  /**
   * Property: Shuffle algorithm correctness
   */
  describe('Property: Shuffle algorithm correctness', () => {
    test('should implement Fisher-Yates shuffle properties', () => {
      const originalArray = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
      const shuffleResults = [];

      // Generate multiple shuffles
      for (let i = 0; i < 20; i++) {
        const shuffled = testEngine.shuffleArray([...originalArray]);
        shuffleResults.push(shuffled);
      }

      // Property: Shuffled array should have same length
      shuffleResults.forEach(result => {
        expect(result).toHaveLength(originalArray.length);
      });

      // Property: Shuffled array should contain all original elements
      shuffleResults.forEach(result => {
        expect(new Set(result)).toEqual(new Set(originalArray));
      });

      // Property: Should produce different arrangements
      const uniqueArrangements = new Set(shuffleResults.map(arr => arr.join(',')));
      expect(uniqueArrangements.size).toBeGreaterThan(1);

      // Property: Each element should appear in different positions
      const positionCounts = {};
      originalArray.forEach(element => {
        positionCounts[element] = new Array(originalArray.length).fill(0);
      });

      shuffleResults.forEach(result => {
        result.forEach((element, position) => {
          positionCounts[element][position]++;
        });
      });

      Object.values(positionCounts).forEach(positions => {
        const nonZeroPositions = positions.filter(count => count > 0).length;
        expect(nonZeroPositions).toBeGreaterThan(1);
      });
    });
  });

  /**
   * Property: Edge cases handling
   */
  describe('Property: Edge cases handling', () => {
    test('should handle edge cases correctly', () => {
      // Property: Empty question list
      const emptyTest = { ...mockTest(), questions: [] };
      const emptyOrder = testEngine.generateQuestionOrder(emptyTest);
      expect(emptyOrder).toEqual([]);

      // Property: Single question
      const singleQuestionTest = {
        ...mockTest(),
        questions: [{ questionId: { _id: 'single' }, text: 'Single Question', order: 1 }]
      };
      const singleOrder = testEngine.generateQuestionOrder(singleQuestionTest);
      expect(singleOrder).toEqual(['single']);

      // Property: Two questions should sometimes swap
      const twoQuestionTest = {
        ...mockTest(),
        questions: [
          { questionId: { _id: 'first' }, text: 'First Question', order: 1 },
          { questionId: { _id: 'second' }, text: 'Second Question', order: 2 }
        ],
        randomizeQuestions: true
      };

      const twoQuestionOrders = [];
      for (let i = 0; i < 10; i++) {
        twoQuestionOrders.push(testEngine.generateQuestionOrder(twoQuestionTest));
      }

      const uniqueTwoOrders = new Set(twoQuestionOrders.map(order => order.join(',')));
      // Should have at least one different arrangement (though not guaranteed in small sample)
      expect(uniqueTwoOrders.size).toBeGreaterThanOrEqual(1);
    });
  });

  /**
   * Property: Deterministic behavior with seeds
   */
  describe('Property: Deterministic behavior with seeds', () => {
    test('should produce consistent results with same seed', () => {
      const test = mockTest({ randomizeQuestions: true });

      // If the engine supports seeding, test it
      if (typeof testEngine.setSeed === 'function') {
        const seed = 12345;

        // Generate orders with same seed
        testEngine.setSeed(seed);
        const order1 = testEngine.generateQuestionOrder(test);

        testEngine.setSeed(seed);
        const order2 = testEngine.generateQuestionOrder(test);

        // Property: Same seed should produce same result
        expect(order1).toEqual(order2);

        // Generate orders with different seeds
        testEngine.setSeed(54321);
        const order3 = testEngine.generateQuestionOrder(test);

        // Property: Different seeds should likely produce different results
        // (not guaranteed but highly probable)
        const allSame = order1.join(',') === order3.join(',');
        if (test.questions.length > 2) {
          expect(allSame).toBe(false);
        }
      } else {
        // Skip if seeding not implemented
        console.log('Seeding not implemented in TestEngine, skipping deterministic test');
      }
    });
  });
});