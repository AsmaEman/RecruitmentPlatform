/**
 * Test model for test configuration and management
 * Requirements: 4.1, 4.2
 */

const mongoose = require('mongoose');

const questionConfigSchema = new mongoose.Schema({
  questionId: { type: mongoose.Schema.Types.ObjectId, ref: 'Question', required: true },
  points: { type: Number, default: 1 },
  timeLimit: { type: Number }, // Override question time limit if needed
  order: { type: Number, required: true }
});

const testSchema = new mongoose.Schema({
  title: { type: String, required: true },
  description: { type: String },

  // Configuration
  questions: [questionConfigSchema],
  totalTimeLimit: { type: Number, required: true }, // Total test time in seconds
  randomizeQuestions: { type: Boolean, default: false },
  randomizeOptions: { type: Boolean, default: false },
  allowReview: { type: Boolean, default: true },
  showResults: { type: Boolean, default: false },

  // Adaptive testing
  isAdaptive: { type: Boolean, default: false },
  adaptiveConfig: {
    startDifficulty: { type: String, enum: ['easy', 'medium', 'hard'], default: 'medium' },
    maxQuestions: { type: Number, default: 20 },
    minQuestions: { type: Number, default: 10 },
    targetAccuracy: { type: Number, default: 0.7 }
  },

  // Access control
  accessCode: { type: String },
  isPublic: { type: Boolean, default: false },
  allowedUsers: [{ type: String }],

  // Scheduling
  startDate: { type: Date },
  endDate: { type: Date },

  // Metadata
  createdBy: { type: String, required: true },
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now },
  isActive: { type: Boolean, default: true }
});

testSchema.index({ createdBy: 1 });
testSchema.index({ startDate: 1, endDate: 1 });
testSchema.index({ isActive: 1, isPublic: 1 });

module.exports = mongoose.model('Test', testSchema);