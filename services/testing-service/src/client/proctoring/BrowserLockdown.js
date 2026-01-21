/**
 * Browser lockdown functionality for secure testing
 * Requirements: 5.1
 */

class BrowserLockdown {
  constructor(options = {}) {
    this.options = {
      enableFullscreen: true,
      blockKeyboardShortcuts: true,
      blockRightClick: true,
      blockTabSwitching: true,
      allowedKeys: ['Tab', 'Enter', 'Escape', 'Backspace', 'Delete', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'],
      ...options
    };

    this.isLocked = false;
    this.violations = [];
    this.eventListeners = [];
    this.onViolation = options.onViolation || (() => { });
  }

  /**
   * Enable browser lockdown
   */
  async enable() {
    try {
      if (this.isLocked) {
        return { success: true, message: 'Already locked' };
      }

      // Request fullscreen
      if (this.options.enableFullscreen) {
        await this.enterFullscreen();
      }

      // Block keyboard shortcuts
      if (this.options.blockKeyboardShortcuts) {
        this.blockKeyboardShortcuts();
      }

      // Block right-click context menu
      if (this.options.blockRightClick) {
        this.blockRightClick();
      }

      // Block tab switching
      if (this.options.blockTabSwitching) {
        this.blockTabSwitching();
      }

      // Monitor window focus
      this.monitorWindowFocus();

      // Block developer tools
      this.blockDevTools();

      // Block text selection and copy/paste
      this.blockTextOperations();

      this.isLocked = true;

      return { success: true, message: 'Browser lockdown enabled' };
    } catch (error) {
      return { success: false, message: error.message };
    }
  }

  /**
   * Disable browser lockdown
   */
  disable() {
    try {
      // Remove all event listeners
      this.eventListeners.forEach(({ element, event, handler }) => {
        element.removeEventListener(event, handler);
      });
      this.eventListeners = [];

      // Exit fullscreen
      if (document.fullscreenElement) {
        document.exitFullscreen();
      }

      this.isLocked = false;

      return { success: true, message: 'Browser lockdown disabled' };
    } catch (error) {
      return { success: false, message: error.message };
    }
  }

  /**
   * Enter fullscreen mode
   */
  async enterFullscreen() {
    const element = document.documentElement;

    if (element.requestFullscreen) {
      await element.requestFullscreen();
    } else if (element.mozRequestFullScreen) {
      await element.mozRequestFullScreen();
    } else if (element.webkitRequestFullscreen) {
      await element.webkitRequestFullscreen();
    } else if (element.msRequestFullscreen) {
      await element.msRequestFullscreen();
    } else {
      throw new Error('Fullscreen not supported');
    }

    // Monitor fullscreen changes
    const fullscreenHandler = () => {
      if (!document.fullscreenElement) {
        this.recordViolation('fullscreen_exit', 'User exited fullscreen mode');
      }
    };

    this.addEventListener(document, 'fullscreenchange', fullscreenHandler);
    this.addEventListener(document, 'webkitfullscreenchange', fullscreenHandler);
    this.addEventListener(document, 'mozfullscreenchange', fullscreenHandler);
    this.addEventListener(document, 'MSFullscreenChange', fullscreenHandler);
  }

  /**
   * Block keyboard shortcuts
   */
  blockKeyboardShortcuts() {
    const keydownHandler = (event) => {
      const { key, ctrlKey, altKey, metaKey, shiftKey } = event;

      // Block common shortcuts
      const blockedShortcuts = [
        // Developer tools
        { key: 'F12' },
        { key: 'I', ctrlKey: true, shiftKey: true },
        { key: 'J', ctrlKey: true, shiftKey: true },
        { key: 'C', ctrlKey: true, shiftKey: true },
        { key: 'U', ctrlKey: true },

        // Navigation
        { key: 'R', ctrlKey: true },
        { key: 'F5' },
        { key: 'T', ctrlKey: true },
        { key: 'N', ctrlKey: true },
        { key: 'W', ctrlKey: true },

        // Tab switching
        { key: 'Tab', altKey: true },
        { key: 'Tab', ctrlKey: true },

        // System shortcuts
        { key: 'D', metaKey: true }, // Show desktop (Mac)
        { key: 'M', metaKey: true }, // Minimize (Mac)
        { key: 'H', metaKey: true }, // Hide (Mac)
      ];

      const isBlocked = blockedShortcuts.some(shortcut => {
        return shortcut.key === key &&
          (shortcut.ctrlKey === undefined || shortcut.ctrlKey === ctrlKey) &&
          (shortcut.altKey === undefined || shortcut.altKey === altKey) &&
          (shortcut.metaKey === undefined || shortcut.metaKey === metaKey) &&
          (shortcut.shiftKey === undefined || shortcut.shiftKey === shiftKey);
      });

      if (isBlocked) {
        event.preventDefault();
        event.stopPropagation();
        this.recordViolation('blocked_shortcut', `Attempted to use blocked shortcut: ${key}`);
        return false;
      }

      // Allow only specific keys for navigation
      if (!this.options.allowedKeys.includes(key) && key.length === 1) {
        // Allow alphanumeric characters for typing
        if (!/^[a-zA-Z0-9\s]$/.test(key)) {
          event.preventDefault();
          this.recordViolation('blocked_key', `Attempted to use blocked key: ${key}`);
          return false;
        }
      }
    };

    this.addEventListener(document, 'keydown', keydownHandler);
  }

  /**
   * Block right-click context menu
   */
  blockRightClick() {
    const contextMenuHandler = (event) => {
      event.preventDefault();
      this.recordViolation('right_click', 'Attempted to open context menu');
      return false;
    };

    this.addEventListener(document, 'contextmenu', contextMenuHandler);
  }

  /**
   * Block tab switching detection
   */
  blockTabSwitching() {
    // Detect Alt+Tab and Ctrl+Tab
    const keydownHandler = (event) => {
      if ((event.altKey && event.key === 'Tab') ||
        (event.ctrlKey && event.key === 'Tab')) {
        event.preventDefault();
        this.recordViolation('tab_switching', 'Attempted to switch tabs');
        return false;
      }
    };

    this.addEventListener(document, 'keydown', keydownHandler);
  }

  /**
   * Monitor window focus changes
   */
  monitorWindowFocus() {
    const blurHandler = () => {
      this.recordViolation('window_blur', 'Window lost focus');
    };

    const focusHandler = () => {
      // Window regained focus
    };

    this.addEventListener(window, 'blur', blurHandler);
    this.addEventListener(window, 'focus', focusHandler);

    // Monitor visibility changes
    const visibilityHandler = () => {
      if (document.hidden) {
        this.recordViolation('tab_hidden', 'Tab became hidden');
      }
    };

    this.addEventListener(document, 'visibilitychange', visibilityHandler);
  }

  /**
   * Block developer tools
   */
  blockDevTools() {
    // Detect developer tools opening by monitoring console
    let devtools = { open: false };

    setInterval(() => {
      const threshold = 160;

      if (window.outerHeight - window.innerHeight > threshold ||
        window.outerWidth - window.innerWidth > threshold) {
        if (!devtools.open) {
          devtools.open = true;
          this.recordViolation('devtools_open', 'Developer tools detected');
        }
      } else {
        devtools.open = false;
      }
    }, 500);

    // Block F12 and other dev tool shortcuts (handled in keyboard shortcuts)
  }

  /**
   * Block text selection and copy/paste operations
   */
  blockTextOperations() {
    const selectStartHandler = (event) => {
      event.preventDefault();
      return false;
    };

    const dragStartHandler = (event) => {
      event.preventDefault();
      return false;
    };

    const copyHandler = (event) => {
      event.preventDefault();
      this.recordViolation('copy_attempt', 'Attempted to copy text');
      return false;
    };

    const pasteHandler = (event) => {
      // Allow paste in input fields for answers
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return true;
      }
      event.preventDefault();
      this.recordViolation('paste_attempt', 'Attempted to paste text');
      return false;
    };

    this.addEventListener(document, 'selectstart', selectStartHandler);
    this.addEventListener(document, 'dragstart', dragStartHandler);
    this.addEventListener(document, 'copy', copyHandler);
    this.addEventListener(document, 'paste', pasteHandler);

    // Disable text selection via CSS
    document.body.style.userSelect = 'none';
    document.body.style.webkitUserSelect = 'none';
    document.body.style.mozUserSelect = 'none';
    document.body.style.msUserSelect = 'none';
  }

  /**
   * Record a violation
   */
  recordViolation(type, message) {
    const violation = {
      type,
      message,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    this.violations.push(violation);

    // Call violation callback
    if (this.onViolation) {
      this.onViolation(violation);
    }

    console.warn('Security violation detected:', violation);
  }

  /**
   * Add event listener and track it for cleanup
   */
  addEventListener(element, event, handler) {
    element.addEventListener(event, handler);
    this.eventListeners.push({ element, event, handler });
  }

  /**
   * Get all recorded violations
   */
  getViolations() {
    return [...this.violations];
  }

  /**
   * Clear violations
   */
  clearViolations() {
    this.violations = [];
  }

  /**
   * Check if browser lockdown is active
   */
  isActive() {
    return this.isLocked;
  }

  /**
   * Get lockdown status
   */
  getStatus() {
    return {
      isLocked: this.isLocked,
      isFullscreen: !!document.fullscreenElement,
      violationCount: this.violations.length,
      lastViolation: this.violations[this.violations.length - 1] || null
    };
  }
}

// Export for use in browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = BrowserLockdown;
} else if (typeof window !== 'undefined') {
  window.BrowserLockdown = BrowserLockdown;
}