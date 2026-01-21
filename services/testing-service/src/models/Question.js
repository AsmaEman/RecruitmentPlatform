/**
 * Question model for test management
 * Requirements: 4.1, 4.2
 */

const mongoose = require('mongoose');

const optionSchema = new mongoose.Schema({
  text: { type: String, required: true },
  isCorrect: { type: Boolean, default: false }
});

const testCaseSchema = new mongoose.Schema({
  input: { type: String, required: true },
  expectedOutput: { type: String, required: true },
  isHidden: { type: Boolean, default: false }
});

const questionSchema = new mongoose.Schema({
  title: { type: String, required: true },
  description: { type: String, required: true },
  type: {
    type: String,
    enum: ['multiple_choice', 'coding', 'essay', 'true_false'],
    required: true
  },
  difficulty: {
    type: String,
    enum: ['easy', 'medium', 'hard'],
    default: 'medium'
  },
  category: { type: String, required: true },
  tags: [{ type: String }],

  // Multiple choice specific
  options: [optionSchema],

  // Coding specific
  language: { type: String },
  starterCode: { type: String },
  testCases: [testCaseSchema],
  timeLimit: { type: Number, default: 3600 }, // seconds
  memoryLimit: { type: Number, default: 128 }, // MB

  // Scoring
  points: { type: Number, default: 1 },

  // Metadata
  createdBy: { type: String, required: true },
  createdAt: { type: Date, default: Date.now },
  updatedAt: { type: Date, default: Date.now },
  isActive: { type: Boolean, default: true }
});

questionSchema.index({ category: 1, difficulty: 1 });
questionSchema.index({ tags: 1 });
questionSchema.index({ type: 1 });

module.exports = mongoose.model('Question', questionSchema);