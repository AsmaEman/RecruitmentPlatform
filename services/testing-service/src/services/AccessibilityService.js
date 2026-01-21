/**
 * Accessibility support service
 * Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
 */

class AccessibilityService {
  constructor() {
    this.logger = require('../utils/logger');
    this.accommodations = new Map(); // In production, use persistent storage
    this.defaultSettings = {
      screenReader: {
        enabled: false,
        ariaLabels: true,
        semanticStructure: true,
        keyboardNavigation: true,
        skipNavigation: true,
        focusManagement: true
      },
      timeAccommodations: {
        enabled: false,
        multiplier: 1.0, // 1.5 for 50% extra time, 2.0 for double time
        unlimitedTime: false,
        breakAllowance: false,
        extendedBreaks: false
      },
      visualAccommodations: {
        highContrast: false,
        fontSize: 'normal', // 'large', 'extra-large'
        colorBlindSupport: false,
        reducedMotion: false
      },
      audioAccommodations: {
        textToSpeech: false,
        closedCaptions: false,
        signLanguage: false,
        audioDescription: false
      }
    };
  }

  /**
   * Set accessibility accommodations for a candidate
   */
  setAccommodations(candidateId, accommodations) {
    try {
      const settings = {
        ...this.defaultSettings,
        ...accommodations,
        candidateId,
        createdAt: new Date(),
        updatedAt: new Date()
      };

      // Validate accommodation settings
      const validation = this.validateAccommodations(settings);
      if (!validation.valid) {
        return {
          success: false,
          error: `Invalid accommodations: ${validation.errors.join(', ')}`
        };
      }

      this.accommodations.set(candidateId, settings);

      this.logger.info(`Accessibility accommodations set for candidate ${candidateId}`);

      return {
        success: true,
        accommodations: settings,
        message: 'Accommodations successfully configured'
      };

    } catch (error) {
      this.logger.error(`Accommodation setup error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Get accessibility accommodations for a candidate
   */
  getAccommodations(candidateId) {
    try {
      const accommodations = this.accommodations.get(candidateId);

      if (!accommodations) {
        return {
          success: true,
          accommodations: { ...this.defaultSettings, candidateId },
          isDefault: true
        };
      }

      return {
        success: true,
        accommodations,
        isDefault: false
      };

    } catch (error) {
      this.logger.error(`Accommodation retrieval error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Generate ARIA labels for test interface elements
   */
  generateAriaLabels(testContent) {
    try {
      const ariaLabels = {
        navigation: {
          'test-progress': `Test progress: ${testContent.currentQuestion || 1} of ${testContent.totalQuestions || 1}`,
          'time-remaining': `Time remaining: ${testContent.timeRemaining || 'unlimited'}`,
          'question-navigation': 'Navigate between questions',
          'submit-test': 'Submit test for grading'
        },
        questions: {},
        controls: {
          'next-question': 'Move to next question',
          'previous-question': 'Move to previous question',
          'flag-question': 'Flag this question for review',
          'clear-answer': 'Clear current answer',
          'save-progress': 'Save current progress'
        }
      };

      // Generate question-specific labels
      if (testContent.questions) {
        testContent.questions.forEach((question, index) => {
          const questionId = question.id || `question-${index + 1}`;
          ariaLabels.questions[questionId] = {
            question: `Question ${index + 1}: ${question.type || 'multiple choice'}`,
            description: question.text ? `Question text: ${question.text.substring(0, 100)}...` : '',
            options: question.options ? question.options.map((opt, i) =>
              `Option ${String.fromCharCode(65 + i)}: ${opt.text || opt}`
            ) : [],
            answer: `Answer for question ${index + 1}`,
            explanation: question.explanation ? `Explanation: ${question.explanation}` : ''
          };
        });
      }

      return {
        success: true,
        ariaLabels,
        generatedAt: new Date()
      };

    } catch (error) {
      this.logger.error(`ARIA label generation error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Generate semantic HTML structure for screen readers
   */
  generateSemanticStructure(testContent) {
    try {
      const structure = {
        landmarks: {
          banner: 'Test header with title and navigation',
          main: 'Main test content area',
          navigation: 'Test navigation and progress',
          complementary: 'Additional test information and tools',
          contentinfo: 'Test footer with submission controls'
        },
        headings: {
          h1: testContent.title || 'Online Assessment',
          h2: [
            'Test Instructions',
            'Question Section',
            'Navigation Controls'
          ],
          h3: testContent.questions ? testContent.questions.map((q, i) =>
            `Question ${i + 1}${q.title ? `: ${q.title}` : ''}`
          ) : []
        },
        regions: {
          'test-instructions': {
            role: 'region',
            'aria-labelledby': 'instructions-heading',
            description: 'Test instructions and guidelines'
          },
          'question-area': {
            role: 'main',
            'aria-labelledby': 'question-heading',
            description: 'Current question and answer options'
          },
          'navigation-area': {
            role: 'navigation',
            'aria-label': 'Test navigation',
            description: 'Question navigation and progress controls'
          }
        },
        skipLinks: [
          { href: '#main-content', text: 'Skip to main content' },
          { href: '#question-area', text: 'Skip to current question' },
          { href: '#navigation-area', text: 'Skip to navigation' },
          { href: '#submit-area', text: 'Skip to submission controls' }
        ]
      };

      return {
        success: true,
        structure,
        generatedAt: new Date()
      };

    } catch (error) {
      this.logger.error(`Semantic structure generation error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Configure keyboard navigation
   */
  configureKeyboardNavigation(testInterface) {
    try {
      const keyboardConfig = {
        shortcuts: {
          'Tab': 'Navigate to next focusable element',
          'Shift+Tab': 'Navigate to previous focusable element',
          'Enter': 'Activate current element',
          'Space': 'Select/toggle current option',
          'Arrow Keys': 'Navigate between options in a group',
          'Escape': 'Cancel current action or close modal',
          'Ctrl+S': 'Save current progress',
          'Ctrl+Enter': 'Submit current answer',
          'F1': 'Open help and accessibility information'
        },
        focusOrder: [
          'skip-links',
          'test-header',
          'instructions-toggle',
          'question-content',
          'answer-options',
          'question-navigation',
          'progress-controls',
          'submit-controls'
        ],
        focusManagement: {
          trapFocus: true, // Keep focus within test area
          restoreFocus: true, // Return focus after modal closes
          skipToContent: true, // Allow skipping repetitive navigation
          visibleFocus: true // Ensure focus indicators are visible
        },
        customHandlers: {
          'question-navigation': {
            'ArrowLeft': 'Previous question',
            'ArrowRight': 'Next question',
            'Home': 'First question',
            'End': 'Last question'
          },
          'answer-selection': {
            'ArrowUp': 'Previous option',
            'ArrowDown': 'Next option',
            'Space': 'Select option',
            'Enter': 'Confirm selection'
          }
        }
      };

      return {
        success: true,
        keyboardConfig,
        generatedAt: new Date()
      };

    } catch (error) {
      this.logger.error(`Keyboard navigation configuration error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Calculate adjusted time limits based on accommodations
   */
  calculateAdjustedTime(originalTimeLimit, candidateId) {
    try {
      const accommodations = this.accommodations.get(candidateId);

      if (!accommodations || !accommodations.timeAccommodations.enabled) {
        return {
          success: true,
          originalTime: originalTimeLimit,
          adjustedTime: originalTimeLimit,
          multiplier: 1.0,
          unlimited: false
        };
      }

      const timeConfig = accommodations.timeAccommodations;

      if (timeConfig.unlimitedTime) {
        return {
          success: true,
          originalTime: originalTimeLimit,
          adjustedTime: null,
          multiplier: null,
          unlimited: true,
          breakAllowance: timeConfig.breakAllowance || false,
          extendedBreaks: timeConfig.extendedBreaks || false,
          message: 'Unlimited time accommodation applied'
        };
      }

      const adjustedTime = Math.round(originalTimeLimit * timeConfig.multiplier);

      this.logger.info(`Time accommodation applied for candidate ${candidateId}: ${originalTimeLimit}min -> ${adjustedTime}min (${timeConfig.multiplier}x)`);

      return {
        success: true,
        originalTime: originalTimeLimit,
        adjustedTime,
        multiplier: timeConfig.multiplier,
        unlimited: false,
        breakAllowance: timeConfig.breakAllowance,
        extendedBreaks: timeConfig.extendedBreaks
      };

    } catch (error) {
      this.logger.error(`Time adjustment calculation error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Generate text-to-speech content
   */
  generateTextToSpeech(content, options = {}) {
    try {
      const ttsConfig = {
        voice: options.voice || 'default',
        rate: options.rate || 1.0,
        pitch: options.pitch || 1.0,
        volume: options.volume || 1.0,
        language: options.language || 'en-US'
      };

      // Process content for TTS
      const processedContent = {
        instructions: this.processTTSText(content.instructions || ''),
        questions: content.questions ? content.questions.map(q => ({
          id: q.id,
          text: this.processTTSText(q.text || ''),
          options: q.options ? q.options.map(opt => this.processTTSText(opt.text || opt)) : [],
          explanation: this.processTTSText(q.explanation || '')
        })) : [],
        navigation: {
          progress: `You are on question ${this.processTTSText(String(content.currentQuestion || 1))} of ${this.processTTSText(String(content.totalQuestions || 1))}`,
          timeRemaining: content.timeRemaining ? `Time remaining: ${this.processTTSText(content.timeRemaining)}` : 'No time limit',
          instructions: 'Use Tab to navigate, Enter to select, and F1 for help'
        }
      };

      return {
        success: true,
        ttsContent: processedContent,
        config: ttsConfig,
        generatedAt: new Date()
      };

    } catch (error) {
      this.logger.error(`Text-to-speech generation error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Apply visual accommodations
   */
  applyVisualAccommodations(candidateId, baseStyles = {}) {
    try {
      const accommodations = this.accommodations.get(candidateId);

      if (!accommodations || !accommodations.visualAccommodations) {
        return {
          success: true,
          styles: baseStyles,
          accommodationsApplied: []
        };
      }

      const visual = accommodations.visualAccommodations;
      const accommodatedStyles = { ...baseStyles };
      const applied = [];

      // High contrast mode
      if (visual.highContrast) {
        accommodatedStyles.backgroundColor = '#000000';
        accommodatedStyles.color = '#ffffff';
        accommodatedStyles.borderColor = '#ffffff';
        accommodatedStyles.linkColor = '#ffff00';
        accommodatedStyles.buttonBackground = '#ffffff';
        accommodatedStyles.buttonColor = '#000000';
        applied.push('high-contrast');
      }

      // Font size adjustments
      if (visual.fontSize !== 'normal') {
        const sizeMultipliers = {
          'large': 1.25,
          'extra-large': 1.5
        };
        const multiplier = sizeMultipliers[visual.fontSize] || 1.0;
        accommodatedStyles.fontSize = `${multiplier}em`;
        accommodatedStyles.lineHeight = `${multiplier * 1.4}em`;
        applied.push(`font-size-${visual.fontSize}`);
      }

      // Color blind support
      if (visual.colorBlindSupport) {
        accommodatedStyles.colorBlindPatterns = true;
        accommodatedStyles.useShapes = true;
        accommodatedStyles.useTextures = true;
        applied.push('color-blind-support');
      }

      // Reduced motion
      if (visual.reducedMotion) {
        accommodatedStyles.animation = 'none';
        accommodatedStyles.transition = 'none';
        accommodatedStyles.transform = 'none';
        applied.push('reduced-motion');
      }

      return {
        success: true,
        styles: accommodatedStyles,
        accommodationsApplied: applied,
        candidateId
      };

    } catch (error) {
      this.logger.error(`Visual accommodations error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  /**
   * Generate closed captions for audio content
   */
  generateClosedCaptions(audioContent, options = {}) {
    try {
      const captions = {
        format: options.format || 'WebVTT',
        language: options.language || 'en-US',
        tracks: []
      };

      if (audioContent.instructions) {
        captions.tracks.push({
          kind: 'captions',
          label: 'Instructions',
          srclang: captions.language,
          content: this.generateCaptionTrack(audioContent.instructions)
        });
      }

      if (audioContent.questions) {
        audioContent.questions.forEach((question, index) => {
          if (question.audio) {
            captions.tracks.push({
              kind: 'captions',
              label: `Question ${index + 1}`,
              srclang: captions.language,
              content: this.generateCaptionTrack(question.audio)
            });
          }
        });
      }

      return {
        success: true,
        captions,
        generatedAt: new Date()
      };

    } catch (error) {
      this.logger.error(`Closed captions generation error: ${error.message}`);
      return { success: false, error: error.message };
    }
  }

  // Helper methods

  validateAccommodations(accommodations) {
    const errors = [];

    // Validate time accommodations
    if (accommodations.timeAccommodations.enabled) {
      const multiplier = accommodations.timeAccommodations.multiplier;
      if (multiplier < 1.0 || multiplier > 5.0) {
        errors.push('Time multiplier must be between 1.0 and 5.0');
      }
    }

    // Validate visual accommodations
    if (accommodations.visualAccommodations.fontSize) {
      const validSizes = ['normal', 'large', 'extra-large'];
      if (!validSizes.includes(accommodations.visualAccommodations.fontSize)) {
        errors.push('Invalid font size option');
      }
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  processTTSText(text) {
    // Clean up text for better TTS pronunciation
    return text
      .replace(/(\d+)\.(\d+)/g, (match, whole, decimal) => {
        // Handle decimal numbers like 3.14159
        const wholeWords = this.numberToWords(whole);
        const decimalDigits = decimal.split('').map(d => this.numberToWords(d)).join(' ');
        return `${wholeWords} point ${decimalDigits}`;
      })
      .replace(/\b(\d+)\b/g, (match, number) => {
        return this.numberToWords(number);
      })
      .replace(/\+/g, ' plus ')
      .replace(/-/g, ' minus ')
      .replace(/\*/g, ' times ')
      .replace(/\//g, ' divided by ')
      .replace(/=/g, ' equals ')
      .replace(/([A-Z]{2,})/g, (match) => {
        // Spell out acronyms
        return match.split('').join(' ');
      })
      .replace(/\s+/g, ' ')
      .trim();
  }

  numberToWords(number) {
    const numberWords = {
      '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four', '5': 'five',
      '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten',
      '11': 'eleven', '12': 'twelve', '13': 'thirteen', '14': 'fourteen', '15': 'fifteen',
      '16': 'sixteen', '17': 'seventeen', '18': 'eighteen', '19': 'nineteen', '20': 'twenty',
      '21': 'twenty one', '22': 'twenty two', '23': 'twenty three', '24': 'twenty four', '25': 'twenty five',
      '26': 'twenty six', '27': 'twenty seven', '28': 'twenty eight', '29': 'twenty nine',
      '30': 'thirty', '40': 'forty', '45': 'forty five', '50': 'fifty', '60': 'sixty', '70': 'seventy',
      '80': 'eighty', '90': 'ninety', '100': 'one hundred', '200': 'two hundred', '300': 'three hundred'
    };
    return numberWords[number] || number;
  }

  generateCaptionTrack(audioData) {
    // Generate WebVTT format captions
    const cues = [];

    if (audioData.transcript) {
      const words = audioData.transcript.split(' ');
      const wordsPerCue = 8;
      const cueLength = 3000; // 3 seconds per cue

      for (let i = 0; i < words.length; i += wordsPerCue) {
        const startTime = (i / wordsPerCue) * cueLength;
        const endTime = startTime + cueLength;
        const cueText = words.slice(i, i + wordsPerCue).join(' ');

        cues.push({
          start: this.formatTimestamp(startTime),
          end: this.formatTimestamp(endTime),
          text: cueText
        });
      }
    }

    return cues;
  }

  formatTimestamp(milliseconds) {
    const totalSeconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    const ms = milliseconds % 1000;

    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }

  /**
   * Get accessibility service statistics
   */
  getServiceStatistics() {
    const totalCandidates = this.accommodations.size;
    let accommodationCounts = {
      screenReader: 0,
      timeAccommodations: 0,
      visualAccommodations: 0,
      audioAccommodations: 0
    };

    for (const [candidateId, accommodations] of this.accommodations.entries()) {
      if (accommodations.screenReader.enabled) accommodationCounts.screenReader++;
      if (accommodations.timeAccommodations.enabled) accommodationCounts.timeAccommodations++;

      // Check if any visual accommodation is enabled
      const visualEnabled = accommodations.visualAccommodations.highContrast ||
        accommodations.visualAccommodations.fontSize !== 'normal' ||
        accommodations.visualAccommodations.colorBlindSupport ||
        accommodations.visualAccommodations.reducedMotion;
      if (visualEnabled) accommodationCounts.visualAccommodations++;

      // Check if any audio accommodation is enabled
      const audioEnabled = accommodations.audioAccommodations.textToSpeech ||
        accommodations.audioAccommodations.closedCaptions ||
        accommodations.audioAccommodations.signLanguage ||
        accommodations.audioAccommodations.audioDescription;
      if (audioEnabled) accommodationCounts.audioAccommodations++;
    }

    return {
      totalCandidates,
      accommodationCounts,
      accommodationPercentages: {
        screenReader: totalCandidates > 0 ? Math.round((accommodationCounts.screenReader / totalCandidates) * 100) : 0,
        timeAccommodations: totalCandidates > 0 ? Math.round((accommodationCounts.timeAccommodations / totalCandidates) * 100) : 0,
        visualAccommodations: totalCandidates > 0 ? Math.round((accommodationCounts.visualAccommodations / totalCandidates) * 100) : 0,
        audioAccommodations: totalCandidates > 0 ? Math.round((accommodationCounts.audioAccommodations / totalCandidates) * 100) : 0
      }
    };
  }
}

module.exports = AccessibilityService;