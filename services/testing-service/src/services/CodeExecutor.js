/**
 * Code execution service with Docker sandboxing
 * Requirements: 4.3, 4.4
 */

const { Docker } = require('node-docker-api');
const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');

class CodeExecutor {
  constructor() {
    this.docker = new Docker({ socketPath: '/var/run/docker.sock' });
    this.logger = require('../utils/logger');

    // Language configurations
    this.languageConfigs = {
      python: {
        image: 'python:3.9-alpine',
        fileExtension: '.py',
        command: ['python', '/code/solution.py'],
        timeout: 30000, // 30 seconds
        memoryLimit: 128 * 1024 * 1024 // 128MB
      },
      javascript: {
        image: 'node:16-alpine',
        fileExtension: '.js',
        command: ['node', '/code/solution.js'],
        timeout: 30000,
        memoryLimit: 128 * 1024 * 1024
      },
      java: {
        image: 'openjdk:11-alpine',
        fileExtension: '.java',
        command: ['sh', '-c', 'cd /code && javac Solution.java && java Solution'],
        timeout: 45000, // Java needs more time for compilation
        memoryLimit: 256 * 1024 * 1024 // 256MB for Java
      },
      cpp: {
        image: 'gcc:9-alpine',
        fileExtension: '.cpp',
        command: ['sh', '-c', 'cd /code && g++ -o solution solution.cpp && ./solution'],
        timeout: 45000,
        memoryLimit: 128 * 1024 * 1024
      }
    };
  }

  /**
   * Execute code in a sandboxed environment
   */
  async executeCode(code, language, testCases = [], timeLimit = null, memoryLimit = null) {
    const executionId = crypto.randomUUID();

    try {
      // Validate language
      const config = this.languageConfigs[language.toLowerCase()];
      if (!config) {
        throw new Error(`Unsupported language: ${language}`);
      }

      // Apply custom limits if provided
      const finalTimeLimit = timeLimit || config.timeout;
      const finalMemoryLimit = memoryLimit || config.memoryLimit;

      // Create temporary directory for code execution
      const tempDir = path.join('/tmp', `code_exec_${executionId}`);
      await fs.mkdir(tempDir, { recursive: true });

      try {
        // Write code to file
        const fileName = language === 'java' ? 'Solution.java' : `solution${config.fileExtension}`;
        const codePath = path.join(tempDir, fileName);
        await fs.writeFile(codePath, code);

        // Execute code with test cases
        const results = [];

        for (let i = 0; i < testCases.length; i++) {
          const testCase = testCases[i];
          const result = await this.runSingleTest(
            tempDir,
            config,
            testCase,
            finalTimeLimit,
            finalMemoryLimit,
            i
          );
          results.push(result);

          // Stop on first failure for efficiency
          if (!result.passed && !testCase.isHidden) {
            break;
          }
        }

        // Calculate overall result
        const passedTests = results.filter(r => r.passed).length;
        const totalTests = results.length;

        return {
          executionId,
          success: true,
          results,
          summary: {
            passed: passedTests,
            total: totalTests,
            score: totalTests > 0 ? (passedTests / totalTests) * 100 : 0
          },
          language,
          executionTime: results.reduce((sum, r) => sum + (r.executionTime || 0), 0)
        };

      } finally {
        // Cleanup temporary directory
        await this.cleanup(tempDir);
      }

    } catch (error) {
      this.logger.error(`Code execution error: ${error.message}`);
      return {
        executionId,
        success: false,
        error: error.message,
        results: [],
        summary: { passed: 0, total: 0, score: 0 }
      };
    }
  }

  /**
   * Run a single test case
   */
  async runSingleTest(codeDir, config, testCase, timeLimit, memoryLimit, testIndex) {
    const startTime = Date.now();

    try {
      // Create container
      const container = await this.docker.container.create({
        Image: config.image,
        Cmd: config.command,
        WorkingDir: '/code',
        HostConfig: {
          Memory: memoryLimit,
          CpuQuota: 50000, // Limit CPU usage
          NetworkMode: 'none', // No network access
          ReadonlyRootfs: false,
          Binds: [`${codeDir}:/code:ro`], // Mount code directory as read-only
          AutoRemove: true
        },
        AttachStdout: true,
        AttachStderr: true,
        AttachStdin: true,
        OpenStdin: true,
        StdinOnce: true
      });

      // Start container
      await container.start();

      // Send input if provided
      if (testCase.input) {
        const stream = await container.attach({
          stream: true,
          stdin: true,
          stdout: true,
          stderr: true
        });

        stream.write(testCase.input + '\n');
        stream.end();
      }

      // Wait for execution with timeout
      const result = await Promise.race([
        container.wait(),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Execution timeout')), timeLimit)
        )
      ]);

      // Get output
      const logs = await container.logs({
        stdout: true,
        stderr: true,
        timestamps: false
      });

      const output = logs.toString().trim();
      const executionTime = Date.now() - startTime;

      // Check if test passed
      const passed = this.compareOutput(output, testCase.expectedOutput);

      return {
        testIndex,
        input: testCase.input,
        expectedOutput: testCase.expectedOutput,
        actualOutput: output,
        passed,
        executionTime,
        exitCode: result.StatusCode
      };

    } catch (error) {
      const executionTime = Date.now() - startTime;

      return {
        testIndex,
        input: testCase.input,
        expectedOutput: testCase.expectedOutput,
        actualOutput: '',
        passed: false,
        executionTime,
        error: error.message,
        exitCode: -1
      };
    }
  }

  /**
   * Compare actual output with expected output
   */
  compareOutput(actual, expected) {
    // Normalize whitespace and line endings
    const normalizeOutput = (str) => {
      return str.trim()
        .replace(/\r\n/g, '\n')
        .replace(/\r/g, '\n')
        .replace(/\s+$/gm, '') // Remove trailing whitespace
        .toLowerCase();
    };

    return normalizeOutput(actual) === normalizeOutput(expected);
  }

  /**
   * Cleanup temporary files and containers
   */
  async cleanup(tempDir) {
    try {
      await fs.rm(tempDir, { recursive: true, force: true });
    } catch (error) {
      this.logger.warn(`Cleanup error: ${error.message}`);
    }
  }

  /**
   * Get supported languages
   */
  getSupportedLanguages() {
    return Object.keys(this.languageConfigs);
  }

  /**
   * Validate code for security issues
   */
  validateCode(code, language) {
    const securityPatterns = {
      python: [
        /import\s+os/i,
        /import\s+subprocess/i,
        /import\s+sys/i,
        /__import__/i,
        /exec\s*\(/i,
        /eval\s*\(/i,
        /open\s*\(/i,
        /file\s*\(/i
      ],
      javascript: [
        /require\s*\(/i,
        /import\s+.*from/i,
        /process\./i,
        /global\./i,
        /eval\s*\(/i,
        /Function\s*\(/i,
        /setTimeout/i,
        /setInterval/i
      ],
      java: [
        /import\s+java\.io/i,
        /import\s+java\.nio/i,
        /import\s+java\.net/i,
        /System\.exit/i,
        /Runtime\.getRuntime/i,
        /ProcessBuilder/i,
        /Class\.forName/i
      ],
      cpp: [
        /#include\s*<fstream>/i,
        /#include\s*<cstdlib>/i,
        /system\s*\(/i,
        /popen\s*\(/i,
        /exec/i
      ]
    };

    const patterns = securityPatterns[language.toLowerCase()] || [];
    const violations = [];

    patterns.forEach(pattern => {
      if (pattern.test(code)) {
        violations.push(`Potentially unsafe code detected: ${pattern.source}`);
      }
    });

    return {
      isValid: violations.length === 0,
      violations
    };
  }

  /**
   * Get execution statistics
   */
  async getExecutionStats() {
    try {
      // Get Docker system info
      const info = await this.docker.info();

      return {
        dockerVersion: info.ServerVersion,
        availableImages: Object.keys(this.languageConfigs),
        memoryLimit: '128MB default',
        timeLimit: '30s default',
        networkAccess: false,
        fileSystemAccess: 'read-only'
      };
    } catch (error) {
      return {
        error: 'Unable to get Docker stats',
        message: error.message
      };
    }
  }
}

module.exports = CodeExecutor;