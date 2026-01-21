/**
 * Monaco Editor integration for in-browser coding
 * Requirements: 4.3
 */

class CodeEditor {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.editor = null;
    this.language = options.language || 'javascript';
    this.theme = options.theme || 'vs-dark';
    this.readOnly = options.readOnly || false;
    this.onChange = options.onChange || (() => { });
    this.onRun = options.onRun || (() => { });

    this.isInitialized = false;
    this.autoSaveInterval = null;
    this.lastSavedContent = '';
  }

  /**
   * Initialize Monaco Editor
   */
  async initialize() {
    try {
      // Load Monaco Editor if not already loaded
      if (typeof monaco === 'undefined') {
        await this.loadMonaco();
      }

      const container = document.getElementById(this.containerId);
      if (!container) {
        throw new Error(`Container with id '${this.containerId}' not found`);
      }

      // Configure Monaco Editor
      this.editor = monaco.editor.create(container, {
        value: '',
        language: this.language,
        theme: this.theme,
        readOnly: this.readOnly,
        automaticLayout: true,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 14,
        lineNumbers: 'on',
        roundedSelection: false,
        scrollbar: {
          vertical: 'visible',
          horizontal: 'visible'
        },
        suggestOnTriggerCharacters: true,
        acceptSuggestionOnEnter: 'on',
        tabCompletion: 'on',
        wordBasedSuggestions: true,
        // Security settings
        links: false,
        contextmenu: false
      });

      // Set up event listeners
      this.setupEventListeners();

      // Set up auto-save
      this.setupAutoSave();

      this.isInitialized = true;
      return { success: true, message: 'Editor initialized successfully' };

    } catch (error) {
      return { success: false, message: error.message };
    }
  }

  /**
   * Load Monaco Editor from CDN
   */
  async loadMonaco() {
    return new Promise((resolve, reject) => {
      // Check if already loaded
      if (window.monaco) {
        resolve();
        return;
      }

      // Create script element
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/monaco-editor@0.34.1/min/vs/loader.js';
      script.onload = () => {
        require.config({
          paths: {
            'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.34.1/min/vs'
          }
        });

        require(['vs/editor/editor.main'], () => {
          resolve();
        });
      };
      script.onerror = () => reject(new Error('Failed to load Monaco Editor'));

      document.head.appendChild(script);
    });
  }

  /**
   * Set up event listeners
   */
  setupEventListeners() {
    if (!this.editor) return;

    // Content change listener
    this.editor.onDidChangeModelContent(() => {
      const content = this.editor.getValue();
      this.onChange(content);
    });

    // Key binding for running code (Ctrl+Enter or Cmd+Enter)
    this.editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      this.runCode();
    });

    // Prevent certain key combinations for security
    this.editor.onKeyDown((e) => {
      // Block F12 (dev tools)
      if (e.keyCode === monaco.KeyCode.F12) {
        e.preventDefault();
        e.stopPropagation();
      }

      // Block Ctrl+Shift+I (dev tools)
      if (e.ctrlKey && e.shiftKey && e.keyCode === monaco.KeyCode.KeyI) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  }

  /**
   * Set up auto-save functionality
   */
  setupAutoSave(intervalMs = 30000) { // 30 seconds
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
    }

    this.autoSaveInterval = setInterval(() => {
      const currentContent = this.getValue();
      if (currentContent !== this.lastSavedContent) {
        this.autoSave(currentContent);
        this.lastSavedContent = currentContent;
      }
    }, intervalMs);
  }

  /**
   * Auto-save current content
   */
  async autoSave(content) {
    try {
      // Send auto-save request to server
      const response = await fetch('/api/test-session/auto-save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          sessionId: this.getSessionId(),
          content: content,
          timestamp: new Date().toISOString()
        })
      });

      if (response.ok) {
        console.log('Auto-save successful');
        this.showAutoSaveIndicator();
      }
    } catch (error) {
      console.warn('Auto-save failed:', error.message);
    }
  }

  /**
   * Show auto-save indicator
   */
  showAutoSaveIndicator() {
    const indicator = document.getElementById('auto-save-indicator');
    if (indicator) {
      indicator.textContent = 'Saved';
      indicator.style.opacity = '1';

      setTimeout(() => {
        indicator.style.opacity = '0';
      }, 2000);
    }
  }

  /**
   * Set editor content
   */
  setValue(content) {
    if (this.editor) {
      this.editor.setValue(content || '');
    }
  }

  /**
   * Get editor content
   */
  getValue() {
    return this.editor ? this.editor.getValue() : '';
  }

  /**
   * Set editor language
   */
  setLanguage(language) {
    if (this.editor) {
      const model = this.editor.getModel();
      monaco.editor.setModelLanguage(model, language);
      this.language = language;
    }
  }

  /**
   * Set editor theme
   */
  setTheme(theme) {
    if (this.editor) {
      monaco.editor.setTheme(theme);
      this.theme = theme;
    }
  }

  /**
   * Set read-only mode
   */
  setReadOnly(readOnly) {
    if (this.editor) {
      this.editor.updateOptions({ readOnly });
      this.readOnly = readOnly;
    }
  }

  /**
   * Focus editor
   */
  focus() {
    if (this.editor) {
      this.editor.focus();
    }
  }

  /**
   * Resize editor
   */
  resize() {
    if (this.editor) {
      this.editor.layout();
    }
  }

  /**
   * Run code
   */
  async runCode() {
    const code = this.getValue();
    if (!code.trim()) {
      this.showMessage('Please enter some code to run', 'warning');
      return;
    }

    try {
      this.showMessage('Running code...', 'info');

      const result = await this.onRun(code, this.language);

      if (result.success) {
        this.showResults(result);
      } else {
        this.showMessage(`Error: ${result.error}`, 'error');
      }
    } catch (error) {
      this.showMessage(`Execution failed: ${error.message}`, 'error');
    }
  }

  /**
   * Show execution results
   */
  showResults(result) {
    const resultsContainer = document.getElementById('execution-results');
    if (!resultsContainer) return;

    let html = '<div class="execution-results">';

    if (result.summary) {
      html += `
        <div class="summary">
          <h4>Test Results</h4>
          <p>Passed: ${result.summary.passed}/${result.summary.total}</p>
          <p>Score: ${result.summary.score.toFixed(1)}%</p>
        </div>
      `;
    }

    if (result.results && result.results.length > 0) {
      html += '<div class="test-cases">';
      result.results.forEach((test, index) => {
        const status = test.passed ? 'passed' : 'failed';
        html += `
          <div class="test-case ${status}">
            <h5>Test Case ${index + 1} - ${status.toUpperCase()}</h5>
            <div class="test-details">
              <p><strong>Input:</strong> <code>${test.input || 'None'}</code></p>
              <p><strong>Expected:</strong> <code>${test.expectedOutput}</code></p>
              <p><strong>Actual:</strong> <code>${test.actualOutput}</code></p>
              <p><strong>Time:</strong> ${test.executionTime}ms</p>
            </div>
          </div>
        `;
      });
      html += '</div>';
    }

    html += '</div>';
    resultsContainer.innerHTML = html;
  }

  /**
   * Show message to user
   */
  showMessage(message, type = 'info') {
    const messageContainer = document.getElementById('editor-messages');
    if (!messageContainer) {
      console.log(`${type.toUpperCase()}: ${message}`);
      return;
    }

    const messageElement = document.createElement('div');
    messageElement.className = `message ${type}`;
    messageElement.textContent = message;

    messageContainer.appendChild(messageElement);

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (messageElement.parentNode) {
        messageElement.parentNode.removeChild(messageElement);
      }
    }, 5000);
  }

  /**
   * Get session ID from URL or storage
   */
  getSessionId() {
    // Try to get from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('sessionId');

    if (sessionId) {
      return sessionId;
    }

    // Try to get from local storage
    return localStorage.getItem('testSessionId');
  }

  /**
   * Dispose editor and cleanup
   */
  dispose() {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
    }

    if (this.editor) {
      this.editor.dispose();
      this.editor = null;
    }

    this.isInitialized = false;
  }

  /**
   * Get editor state for recovery
   */
  getState() {
    return {
      content: this.getValue(),
      language: this.language,
      theme: this.theme,
      readOnly: this.readOnly,
      cursorPosition: this.editor ? this.editor.getPosition() : null
    };
  }

  /**
   * Restore editor state
   */
  restoreState(state) {
    if (state.content) {
      this.setValue(state.content);
    }

    if (state.language) {
      this.setLanguage(state.language);
    }

    if (state.theme) {
      this.setTheme(state.theme);
    }

    if (state.readOnly !== undefined) {
      this.setReadOnly(state.readOnly);
    }

    if (state.cursorPosition && this.editor) {
      this.editor.setPosition(state.cursorPosition);
    }
  }
}

// Export for use in browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CodeEditor;
} else if (typeof window !== 'undefined') {
  window.CodeEditor = CodeEditor;
}