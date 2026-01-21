/**
 * Test session model for tracking test attempts
 * Requirements: 4.1, 4.5, 4.6
 */

const mongoose = require('mongoose');

const answerSchema = new mongoose.Schema({
  questionId: { type: mongoose.Schema.Types.ObjectId, ref: 'Question', required: true },
  answer: { type: mongoose.Schema.Types.Mixed }, // Can be string, array, or object
  isCorrect: { type: Boolean },
  points: { type: Number, default: 0 },
  timeSpent: { type: Number, default: 0 }, // seconds
  submittedAt: { type: Date }
});

const testSessionSchema = new mongoose.Schema({
  testId: { type: mongoose.Schema.Types.ObjectId, ref: 'Test', required: true },
  candidateId: { type: String, required: true },
  candidateEmail: { type: String, required: true },

  // Session state
  status: {
    type: String,
    enum: ['not_started', 'in_progress', 'paused', 'completed', 'expired', 'terminated'],
    default: 'not_started'
  },

  // Timing
  startedAt: { type: Date },
  completedAt: { type: Date },
  lastActivity: { type: Date, default: Date.now },
  timeRemaining: { type: Number }, // seconds

  // Answers and progress
  answers: [answerSchema],
  currentQuestionIndex: { type: Number, default: 0 },
  questionsOrder: [{ type: mongoose.Schema.Types.ObjectId, ref: 'Question' }],

  // Scoring
  totalScore: { type: Number, default: 0 },
  maxScore: { type: Number, default: 0 },
  percentage: { type: Number, default: 0 },

  // Auto-save data
  autoSaveData: { type: mongoose.Schema.Types.Mixed },
  lastAutoSave: { type: Date },

  // Security and monitoring
  ipAddress: { type: String },
  userAgent: { type: String },
  violations: [{
    type: { type: String, required: true },
    timestamp: { type: Date, default: Date.now },
    details: { type: mongoose.Schema.Types.Mixed }
  }],

  // Adaptive testing
  difficultyLevel: { type: String, enum: ['easy', 'medium', 'hard'], default: 'medium' },
  accuracyRate: { type: Number, default: 0 },

  // Metadata
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now }
});

testSessionSchema.index({ candidateId: 1, testId: 1 });
testSessionSchema.index({ status: 1 });
testSessionSchema.index({ lastActivity: 1 });
testSessionSchema.index({ createdAt: 1 });

// Auto-update lastActivity on save
testSessionSchema.pre('save', function (next) {
  this.lastActivity = new Date();
  this.updatedAt = new Date();
  next();
});

module.exports = mongoose.model('TestSession', testSessionSchema);