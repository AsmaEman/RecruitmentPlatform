/**
 * Property test for browser lockdown enforcement.
 * 
 * **Property 11: Browser Lockdown Enforcement**
 * **Validates: Requirements 5.1**
 * 
 * Feature: recruitment-testing-platform, Property 11: Browser Lockdown Enforcement
 */

const { expect } = require('chai');
const jsdom = require('jsdom');
const { JSDOM } = jsdom;

// Mock browser environment
const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>', {
  url: 'http://localhost',
  pretendToBeVisual: true,
  resources: 'usable'
});

global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;

const BrowserLockdown = require('../client/proctoring/BrowserLockdown');

describe('Browser Lockdown Property Tests', () => {
  let lockdown;

  beforeEach(() => {
    // Reset DOM
    document.body.innerHTML = '';
    document.body.style.cssText = '';

    lockdown = new BrowserLockdown({
      enableFullscreen: false, // Skip fullscreen in tests
      onViolation: () => { } // Silent violations in tests
    });
  });

  afterEach(() => {
    if (lockdown) {
      lockdown.disable();
    }
  });

  describe('Property: Lockdown state consistency', () => {
    it('should maintain consistent state across enable/disable cycles', async () => {
      // Property: Initial state should be unlocked
      expect(lockdown.isActive()).to.be.false;
      expect(lockdown.getViolations()).to.have.length(0);

      // Property: After enabling, should be locked
      const enableResult = await lockdown.enable();
      expect(enableResult.success).to.be.true;
      expect(lockdown.isActive()).to.be.true;

      // Property: After disabling, should be unlocked
      const disableResult = lockdown.disable();
      expect(disableResult.success).to.be.true;
      expect(lockdown.isActive()).to.be.false;

      // Property: Multiple enable calls should be idempotent
      await lockdown.enable();
      const secondEnable = await lockdown.enable();
      expect(secondEnable.success).to.be.true;
      expect(lockdown.isActive()).to.be.true;
    });
  });

  describe('Property: Violation detection consistency', () => {
    it('should consistently detect and record violations', async () => {
      await lockdown.enable();

      const initialViolationCount = lockdown.getViolations().length;

      // Property: Right-click should generate violation
      const rightClickEvent = new dom.window.MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true,
        button: 2
      });

      document.dispatchEvent(rightClickEvent);

      const violationsAfterRightClick = lockdown.getViolations();
      expect(violationsAfterRightClick.length).to.be.greaterThan(initialViolationCount);

      // Property: Violations should have required structure
      const lastViolation = violationsAfterRightClick[violationsAfterRightClick.length - 1];
      expect(lastViolation).to.have.property('type');
      expect(lastViolation).to.have.property('message');
      expect(lastViolation).to.have.property('timestamp');
      expect(lastViolation.type).to.equal('right_click');
    });

    it('should detect blocked keyboard shortcuts', async () => {
      await lockdown.enable();

      const blockedShortcuts = [
        { key: 'F12' },
        { key: 'I', ctrlKey: true, shiftKey: true },
        { key: 'U', ctrlKey: true },
        { key: 'R', ctrlKey: true }
      ];

      for (const shortcut of blockedShortcuts) {
        const initialCount = lockdown.getViolations().length;

        // Property: Each blocked shortcut should generate a violation
        const keyEvent = new dom.window.KeyboardEvent('keydown', {
          key: shortcut.key,
          ctrlKey: shortcut.ctrlKey || false,
          shiftKey: shortcut.shiftKey || false,
          bubbles: true,
          cancelable: true
        });

        document.dispatchEvent(keyEvent);

        const newCount = lockdown.getViolations().length;
        expect(newCount).to.be.greaterThan(initialCount,
          `Shortcut ${shortcut.key} should generate violation`);
      }
    });
  });

  describe('Property: Event listener management', () => {
    it('should properly manage event listeners lifecycle', async () => {
      // Property: Enabling should add event listeners
      await lockdown.enable();
      expect(lockdown.eventListeners.length).to.be.greaterThan(0);

      const listenerCount = lockdown.eventListeners.length;

      // Property: Disabling should remove all event listeners
      lockdown.disable();
      expect(lockdown.eventListeners.length).to.equal(0);

      // Property: Re-enabling should add listeners again
      await lockdown.enable();
      expect(lockdown.eventListeners.length).to.equal(listenerCount);
    });
  });

  describe('Property: Text selection blocking', () => {
    it('should consistently block text selection operations', async () => {
      await lockdown.enable();

      // Property: Text selection should be disabled via CSS
      const bodyStyle = document.body.style;
      expect(bodyStyle.userSelect).to.equal('none');
      expect(bodyStyle.webkitUserSelect).to.equal('none');
      expect(bodyStyle.mozUserSelect).to.equal('none');
      expect(bodyStyle.msUserSelect).to.equal('none');

      // Property: Select start events should be blocked
      const initialViolationCount = lockdown.getViolations().length;

      const selectEvent = new dom.window.Event('selectstart', {
        bubbles: true,
        cancelable: true
      });

      document.dispatchEvent(selectEvent);

      // Should not generate violation for selectstart (just prevented)
      // But copy attempts should generate violations
      const copyEvent = new dom.window.Event('copy', {
        bubbles: true,
        cancelable: true
      });

      document.dispatchEvent(copyEvent);

      const violationsAfterCopy = lockdown.getViolations();
      expect(violationsAfterCopy.length).to.be.greaterThan(initialViolationCount);

      const copyViolation = violationsAfterCopy.find(v => v.type === 'copy_attempt');
      expect(copyViolation).to.exist;
    });
  });

  describe('Property: Configuration consistency', () => {
    it('should respect configuration options consistently', async () => {
      // Test with different configurations
      const configs = [
        { blockRightClick: false, blockKeyboardShortcuts: true },
        { blockRightClick: true, blockKeyboardShortcuts: false },
        { blockRightClick: true, blockKeyboardShortcuts: true }
      ];

      for (const config of configs) {
        const configuredLockdown = new BrowserLockdown(config);
        await configuredLockdown.enable();

        // Property: Right-click blocking should respect configuration
        const rightClickEvent = new dom.window.MouseEvent('contextmenu', {
          bubbles: true,
          cancelable: true
        });

        document.dispatchEvent(rightClickEvent);

        const violations = configuredLockdown.getViolations();
        const hasRightClickViolation = violations.some(v => v.type === 'right_click');

        if (config.blockRightClick) {
          expect(hasRightClickViolation).to.be.true;
        } else {
          expect(hasRightClickViolation).to.be.false;
        }

        configuredLockdown.disable();
      }
    });
  });

  describe('Property: Status reporting accuracy', () => {
    it('should accurately report lockdown status', async () => {
      // Property: Initial status should reflect unlocked state
      let status = lockdown.getStatus();
      expect(status.isLocked).to.be.false;
      expect(status.violationCount).to.equal(0);
      expect(status.lastViolation).to.be.null;

      // Property: Status after enabling should reflect locked state
      await lockdown.enable();
      status = lockdown.getStatus();
      expect(status.isLocked).to.be.true;

      // Property: Status should update with violations
      const rightClickEvent = new dom.window.MouseEvent('contextmenu', {
        bubbles: true,
        cancelable: true
      });
      document.dispatchEvent(rightClickEvent);

      status = lockdown.getStatus();
      expect(status.violationCount).to.be.greaterThan(0);
      expect(status.lastViolation).to.not.be.null;
      expect(status.lastViolation.type).to.equal('right_click');
    });
  });

  describe('Property: Violation data integrity', () => {
    it('should maintain violation data integrity', async () => {
      await lockdown.enable();

      // Generate multiple violations
      const violationTypes = ['contextmenu', 'copy', 'selectstart'];

      for (const eventType of violationTypes) {
        const event = new dom.window.Event(eventType, {
          bubbles: true,
          cancelable: true
        });
        document.dispatchEvent(event);
      }

      const violations = lockdown.getViolations();

      // Property: Each violation should have complete data
      violations.forEach(violation => {
        expect(violation).to.have.property('type');
        expect(violation).to.have.property('message');
        expect(violation).to.have.property('timestamp');
        expect(violation).to.have.property('userAgent');
        expect(violation).to.have.property('url');

        // Property: Timestamp should be valid ISO string
        expect(() => new Date(violation.timestamp)).to.not.throw();

        // Property: Type should be non-empty string
        expect(violation.type).to.be.a('string').that.is.not.empty;

        // Property: Message should be descriptive
        expect(violation.message).to.be.a('string').that.is.not.empty;
      });

      // Property: Violations should be in chronological order
      for (let i = 1; i < violations.length; i++) {
        const prevTime = new Date(violations[i - 1].timestamp);
        const currTime = new Date(violations[i].timestamp);
        expect(currTime.getTime()).to.be.at.least(prevTime.getTime());
      }
    });
  });
});