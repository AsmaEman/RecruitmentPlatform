/**
 * Property test for time extension application
 * Property 18: Time Extension Application
 * Validates: Requirements 7.2
 */

const AccessibilityService = require('../services/AccessibilityService');

describe('Property Test: Time Extension Application', () => {
  let accessibilityService;

  beforeEach(() => {
    accessibilityService = new AccessibilityService();
  });

  afterEach(() => {
    // Cleanup test data
    accessibilityService.accommodations.clear();
  });

  /**
   * Property: Time multipliers must be applied correctly
   * Invariant: Adjusted time must equal original time * multiplier
   */
  describe('Time Multiplier Property', () => {
    test('should apply time multipliers correctly', () => {
      const candidateId = 'time-candidate-1';
      const originalTime = 60; // 60 minutes

      // Test different multipliers
      const multipliers = [1.25, 1.5, 2.0, 3.0];

      for (const multiplier of multipliers) {
        const accommodations = {
          timeAccommodations: {
            enabled: true,
            multiplier: multiplier,
            unlimitedTime: false
          }
        };

        const setResult = accessibilityService.setAccommodations(candidateId, accommodations);
        expect(setResult.success).toBe(true);

        const timeResult = accessibilityService.calculateAdjustedTime(originalTime, candidateId);
        expect(timeResult.success).toBe(true);

        // Property: Adjusted time must equal original * multiplier
        const expectedTime = Math.round(originalTime * multiplier);
        expect(timeResult.adjustedTime).toBe(expectedTime);
        expect(timeResult.multiplier).toBe(multiplier);
        expect(timeResult.originalTime).toBe(originalTime);
        expect(timeResult.unlimited).toBe(false);
      }
    });

    test('should handle unlimited time accommodation', () => {
      const candidateId = 'unlimited-candidate';
      const originalTime = 90;

      const accommodations = {
        timeAccommodations: {
          enabled: true,
          unlimitedTime: true,
          multiplier: 2.0 // Should be ignored when unlimited is true
        }
      };

      const setResult = accessibilityService.setAccommodations(candidateId, accommodations);
      expect(setResult.success).toBe(true);

      const timeResult = accessibilityService.calculateAdjustedTime(originalTime, candidateId);
      expect(timeResult.success).toBe(true);

      // Property: Unlimited time should override multiplier
      expect(timeResult.unlimited).toBe(true);
      expect(timeResult.adjustedTime).toBeNull();
      expect(timeResult.multiplier).toBeNull();
      expect(timeResult.originalTime).toBe(originalTime);
      expect(timeResult.message).toContain('Unlimited time accommodation');
    });

    test('should return original time when no accommodations are set', () => {
      const candidateId = 'no-accommodations-candidate';
      const originalTime = 45;

      const timeResult = accessibilityService.calculateAdjustedTime(originalTime, candidateId);
      expect(timeResult.success).toBe(true);

      // Property: No accommodations should return original time
      expect(timeResult.adjustedTime).toBe(originalTime);
      expect(timeResult.originalTime).toBe(originalTime);
      expect(timeResult.multiplier).toBe(1.0);
      expect(timeResult.unlimited).toBe(false);
    });

    test('should handle disabled time accommodations', () => {
      const candidateId = 'disabled-accommodations-candidate';
      const originalTime = 120;

      const accommodations = {
        timeAccommodations: {
          enabled: false,
          multiplier: 2.0,
          unlimitedTime: true
        }
      };

      const setResult = accessibilityService.setAccommodations(candidateId, accommodations);
      expect(setResult.success).toBe(true);

      const timeResult = accessibilityService.calculateAdjustedTime(originalTime, candidateId);
      expect(timeResult.success).toBe(true);

      // Property: Disabled accommodations should return original time
      expect(timeResult.adjustedTime).toBe(originalTime);
      expect(timeResult.multiplier).toBe(1.0);
      expect(timeResult.unlimited).toBe(false);
    });
  });

  /**
   * Property: Time accommodations must be validated
   * Invariant: Invalid multipliers must be rejected
   */
  describe('Time Accommodation Validation Property', () => {
    test('should validate time multiplier ranges', () => {
      const candidateId = 'validation-candidate';

      // Test invalid multipliers
      const invalidMultipliers = [0.5, 0.9, 5.1, 10.0, -1.0];

      for (const multiplier of invalidMultipliers) {
        const accommodations = {
          timeAccommodations: {
            enabled: true,
            multiplier: multiplier
          }
        };

        const result = accessibilityService.setAccommodations(candidateId, accommodations);

        // Property: Invalid multipliers should be rejected
        expect(result.success).toBe(false);
        expect(result.error).toContain('Invalid accommodations');
        expect(result.error).toContain('Time multiplier must be between 1.0 and 5.0');
      }
    });

    test('should accept valid time multipliers', () => {
      const candidateId = 'valid-candidate';

      // Test valid multipliers
      const validMultipliers = [1.0, 1.25, 1.5, 2.0, 3.0, 4.0, 5.0];

      for (const multiplier of validMultipliers) {
        const accommodations = {
          timeAccommodations: {
            enabled: true,
            multiplier: multiplier
          }
        };

        const result = accessibilityService.setAccommodations(candidateId, accommodations);

        // Property: Valid multipliers should be accepted
        expect(result.success).toBe(true);
        expect(result.accommodations.timeAccommodations.multiplier).toBe(multiplier);
      }
    });
  });

  /**
   * Property: Break allowances must be properly configured
   * Invariant: Break settings must be preserved and retrievable
   */
  describe('Break Allowance Property', () => {
    test('should configure break allowances correctly', () => {
      const candidateId = 'break-candidate';

      const accommodations = {
        timeAccommodations: {
          enabled: true,
          multiplier: 1.5,
          breakAllowance: true,
          extendedBreaks: true
        }
      };

      const setResult = accessibilityService.setAccommodations(candidateId, accommodations);
      expect(setResult.success).toBe(true);

      const timeResult = accessibilityService.calculateAdjustedTime(60, candidateId);
      expect(timeResult.success).toBe(true);

      // Property: Break settings must be preserved
      expect(timeResult.breakAllowance).toBe(true);
      expect(timeResult.extendedBreaks).toBe(true);

      // Property: Break settings must be retrievable
      const retrieved = accessibilityService.getAccommodations(candidateId);
      expect(retrieved.success).toBe(true);
      expect(retrieved.accommodations.timeAccommodations.breakAllowance).toBe(true);
      expect(retrieved.accommodations.timeAccommodations.extendedBreaks).toBe(true);
    });

    test('should handle break allowances with unlimited time', () => {
      const candidateId = 'unlimited-break-candidate';

      const accommodations = {
        timeAccommodations: {
          enabled: true,
          unlimitedTime: true,
          breakAllowance: true,
          extendedBreaks: true
        }
      };

      const setResult = accessibilityService.setAccommodations(candidateId, accommodations);
      expect(setResult.success).toBe(true);

      const timeResult = accessibilityService.calculateAdjustedTime(90, candidateId);
      expect(timeResult.success).toBe(true);

      // Property: Break settings should work with unlimited time
      expect(timeResult.unlimited).toBe(true);
      expect(timeResult.breakAllowance).toBe(true);
      expect(timeResult.extendedBreaks).toBe(true);
    });
  });

  /**
   * Property: Time calculations must be consistent
   * Invariant: Same inputs must produce same outputs
   */
  describe('Time Calculation Consistency Property', () => {
    test('should produce consistent results for same inputs', () => {
      const candidateId = 'consistency-candidate';
      const originalTime = 75;

      const accommodations = {
        timeAccommodations: {
          enabled: true,
          multiplier: 1.5
        }
      };

      const setResult = accessibilityService.setAccommodations(candidateId, accommodations);
      expect(setResult.success).toBe(true);

      // Calculate time multiple times
      const results = [];
      for (let i = 0; i < 10; i++) {
        const timeResult = accessibilityService.calculateAdjustedTime(originalTime, candidateId);
        expect(timeResult.success).toBe(true);
        results.push(timeResult);
      }

      // Property: All results should be identical
      const firstResult = results[0];
      for (const result of results) {
        expect(result.adjustedTime).toBe(firstResult.adjustedTime);
        expect(result.multiplier).toBe(firstResult.multiplier);
        expect(result.originalTime).toBe(firstResult.originalTime);
        expect(result.unlimited).toBe(firstResult.unlimited);
      }

      // Property: Calculated time should be correct
      const expectedTime = Math.round(originalTime * 1.5);
      expect(firstResult.adjustedTime).toBe(expectedTime);
    });

    test('should handle edge cases in time calculations', () => {
      const candidateId = 'edge-case-candidate';

      const accommodations = {
        timeAccommodations: {
          enabled: true,
          multiplier: 1.5
        }
      };

      const setResult = accessibilityService.setAccommodations(candidateId, accommodations);
      expect(setResult.success).toBe(true);

      // Test edge cases
      const edgeCases = [
        { original: 0, expected: 0 },
        { original: 1, expected: 2 }, // Math.round(1 * 1.5) = 2
        { original: 3, expected: 5 }, // Math.round(3 * 1.5) = 5
        { original: 1000, expected: 1500 }
      ];

      for (const testCase of edgeCases) {
        const timeResult = accessibilityService.calculateAdjustedTime(testCase.original, candidateId);
        expect(timeResult.success).toBe(true);

        // Property: Edge cases should be handled correctly
        expect(timeResult.adjustedTime).toBe(testCase.expected);
        expect(timeResult.originalTime).toBe(testCase.original);
      }
    });
  });

  /**
   * Property: Multiple candidates must be handled independently
   * Invariant: One candidate's accommodations must not affect another's
   */
  describe('Candidate Independence Property', () => {
    test('should handle multiple candidates with different time accommodations', () => {
      const candidates = [
        {
          id: 'candidate-1',
          accommodations: {
            timeAccommodations: {
              enabled: true,
              multiplier: 1.25
            }
          }
        },
        {
          id: 'candidate-2',
          accommodations: {
            timeAccommodations: {
              enabled: true,
              multiplier: 2.0,
              breakAllowance: true
            }
          }
        },
        {
          id: 'candidate-3',
          accommodations: {
            timeAccommodations: {
              enabled: true,
              unlimitedTime: true
            }
          }
        },
        {
          id: 'candidate-4',
          accommodations: {
            timeAccommodations: {
              enabled: false
            }
          }
        }
      ];

      // Set accommodations for all candidates
      for (const candidate of candidates) {
        const result = accessibilityService.setAccommodations(candidate.id, candidate.accommodations);
        expect(result.success).toBe(true);
      }

      const originalTime = 60;

      // Test candidate 1 (1.25x multiplier)
      const result1 = accessibilityService.calculateAdjustedTime(originalTime, candidates[0].id);
      expect(result1.success).toBe(true);
      expect(result1.adjustedTime).toBe(75); // 60 * 1.25 = 75
      expect(result1.multiplier).toBe(1.25);
      expect(result1.unlimited).toBe(false);

      // Test candidate 2 (2.0x multiplier with breaks)
      const result2 = accessibilityService.calculateAdjustedTime(originalTime, candidates[1].id);
      expect(result2.success).toBe(true);
      expect(result2.adjustedTime).toBe(120); // 60 * 2.0 = 120
      expect(result2.multiplier).toBe(2.0);
      expect(result2.breakAllowance).toBe(true);
      expect(result2.unlimited).toBe(false);

      // Test candidate 3 (unlimited time)
      const result3 = accessibilityService.calculateAdjustedTime(originalTime, candidates[2].id);
      expect(result3.success).toBe(true);
      expect(result3.unlimited).toBe(true);
      expect(result3.adjustedTime).toBeNull();

      // Test candidate 4 (no accommodations)
      const result4 = accessibilityService.calculateAdjustedTime(originalTime, candidates[3].id);
      expect(result4.success).toBe(true);
      expect(result4.adjustedTime).toBe(originalTime);
      expect(result4.multiplier).toBe(1.0);
      expect(result4.unlimited).toBe(false);

      // Property: Each candidate's results should be independent
      expect(result1.adjustedTime).not.toBe(result2.adjustedTime);
      expect(result2.unlimited).not.toBe(result3.unlimited);
      expect(result3.multiplier).not.toBe(result4.multiplier);
    });

    test('should maintain candidate isolation during concurrent operations', () => {
      const candidateIds = ['concurrent-1', 'concurrent-2', 'concurrent-3'];
      const multipliers = [1.25, 1.5, 2.0];

      // Set up accommodations concurrently
      const setupPromises = candidateIds.map((id, index) => {
        const accommodations = {
          timeAccommodations: {
            enabled: true,
            multiplier: multipliers[index]
          }
        };
        return accessibilityService.setAccommodations(id, accommodations);
      });

      // Wait for all setups to complete
      const setupResults = setupPromises;
      for (const result of setupResults) {
        expect(result.success).toBe(true);
      }

      // Calculate times concurrently
      const originalTime = 100;
      const calculationPromises = candidateIds.map(id =>
        accessibilityService.calculateAdjustedTime(originalTime, id)
      );

      const calculationResults = calculationPromises;

      // Property: Concurrent operations should not interfere
      expect(calculationResults[0].adjustedTime).toBe(125); // 100 * 1.25
      expect(calculationResults[1].adjustedTime).toBe(150); // 100 * 1.5
      expect(calculationResults[2].adjustedTime).toBe(200); // 100 * 2.0

      // Property: Each candidate should maintain their specific multiplier
      expect(calculationResults[0].multiplier).toBe(1.25);
      expect(calculationResults[1].multiplier).toBe(1.5);
      expect(calculationResults[2].multiplier).toBe(2.0);
    });
  });

  /**
   * Property: Time accommodation statistics must be accurate
   * Invariant: Statistics must reflect actual accommodation usage
   */
  describe('Time Accommodation Statistics Property', () => {
    test('should track time accommodation usage accurately', () => {
      const candidates = [
        {
          id: 'stats-candidate-1',
          accommodations: {
            timeAccommodations: { enabled: true, multiplier: 1.5 },
            screenReader: { enabled: false }
          }
        },
        {
          id: 'stats-candidate-2',
          accommodations: {
            timeAccommodations: { enabled: true, unlimitedTime: true },
            visualAccommodations: { fontSize: 'large' }
          }
        },
        {
          id: 'stats-candidate-3',
          accommodations: {
            screenReader: { enabled: true },
            visualAccommodations: { highContrast: true }
          }
        }
      ];

      // Set accommodations
      for (const candidate of candidates) {
        const result = accessibilityService.setAccommodations(candidate.id, candidate.accommodations);
        expect(result.success).toBe(true);
      }

      const stats = accessibilityService.getServiceStatistics();

      // Property: Time accommodation count should be accurate
      expect(stats.accommodationCounts.timeAccommodations).toBe(2); // candidates 1 and 2

      // Property: Percentage should be calculated correctly
      expect(stats.accommodationPercentages.timeAccommodations).toBe(67); // 2/3 * 100 = 67%

      // Property: Other accommodation types should also be tracked
      expect(stats.accommodationCounts.screenReader).toBe(1); // candidate 3
      expect(stats.accommodationCounts.visualAccommodations).toBe(2); // candidates 2 and 3
    });

    test('should handle empty statistics correctly', () => {
      const stats = accessibilityService.getServiceStatistics();

      expect(stats.totalCandidates).toBe(0);
      expect(stats.accommodationCounts.timeAccommodations).toBe(0);
      expect(stats.accommodationPercentages.timeAccommodations).toBe(0);
    });
  });

  /**
   * Property: Time accommodations must integrate with other accessibility features
   * Invariant: Time accommodations must not conflict with other features
   */
  describe('Integration Property', () => {
    test('should integrate time accommodations with other accessibility features', () => {
      const candidateId = 'integration-candidate';

      const accommodations = {
        timeAccommodations: {
          enabled: true,
          multiplier: 2.0,
          breakAllowance: true
        },
        screenReader: {
          enabled: true,
          ariaLabels: true
        },
        visualAccommodations: {
          fontSize: 'large',
          highContrast: true
        }
      };

      const setResult = accessibilityService.setAccommodations(candidateId, accommodations);
      expect(setResult.success).toBe(true);

      // Property: Time accommodations should work alongside other features
      const timeResult = accessibilityService.calculateAdjustedTime(60, candidateId);
      expect(timeResult.success).toBe(true);
      expect(timeResult.adjustedTime).toBe(120);
      expect(timeResult.breakAllowance).toBe(true);

      // Property: Other accommodations should remain intact
      const retrieved = accessibilityService.getAccommodations(candidateId);
      expect(retrieved.success).toBe(true);
      expect(retrieved.accommodations.screenReader.enabled).toBe(true);
      expect(retrieved.accommodations.visualAccommodations.fontSize).toBe('large');
      expect(retrieved.accommodations.visualAccommodations.highContrast).toBe(true);

      // Property: Visual accommodations should still work
      const visualResult = accessibilityService.applyVisualAccommodations(candidateId);
      expect(visualResult.success).toBe(true);
      expect(visualResult.accommodationsApplied).toContain('font-size-large');
      expect(visualResult.accommodationsApplied).toContain('high-contrast');
    });
  });
});