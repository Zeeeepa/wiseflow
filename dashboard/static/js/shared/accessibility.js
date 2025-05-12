/**
 * Accessibility - Utilities for enhancing accessibility in Wiseflow UI components
 * 
 * This module provides utilities and helpers for implementing accessible UI components
 * in the Wiseflow application, including focus management, keyboard navigation,
 * and ARIA attribute handling.
 */

const Accessibility = (function() {
    // Last focused element before a modal/dialog was opened
    let lastFocusedElement = null;
    
    // Currently active focus trap (for modals/dialogs)
    let activeFocusTrap = null;
    
    // Focus history for navigation
    const focusHistory = [];
    
    // Keyboard shortcuts registry
    const keyboardShortcuts = {};
    
    // Initialize keyboard shortcut listener
    document.addEventListener('keydown', function(event) {
        // Check for registered shortcuts
        const key = `${event.key}${event.ctrlKey ? '+ctrl' : ''}${event.altKey ? '+alt' : ''}${event.shiftKey ? '+shift' : ''}`;
        
        if (keyboardShortcuts[key]) {
            const shortcut = keyboardShortcuts[key];
            
            // Check if shortcut is context-sensitive
            if (shortcut.context && !shortcut.context()) {
                return;
            }
            
            // Execute shortcut handler
            shortcut.handler(event);
            
            // Prevent default if specified
            if (shortcut.preventDefault) {
                event.preventDefault();
            }
        }
    });
    
    return {
        /**
         * Register a keyboard shortcut
         * @param {string} key - Key or key combination (e.g., 'Escape', 'Enter', 'a+ctrl')
         * @param {Function} handler - Function to call when shortcut is triggered
         * @param {Object} options - Additional options
         * @param {Function} options.context - Function that returns true if shortcut should be active
         * @param {boolean} options.preventDefault - Whether to prevent default browser behavior
         */
        registerShortcut: function(key, handler, options = {}) {
            keyboardShortcuts[key] = {
                handler,
                context: options.context,
                preventDefault: options.preventDefault !== false
            };
        },
        
        /**
         * Unregister a keyboard shortcut
         * @param {string} key - Key or key combination to unregister
         */
        unregisterShortcut: function(key) {
            delete keyboardShortcuts[key];
        },
        
        /**
         * Save the currently focused element
         * @returns {Element} The saved element
         */
        saveFocus: function() {
            lastFocusedElement = document.activeElement;
            focusHistory.push(lastFocusedElement);
            return lastFocusedElement;
        },
        
        /**
         * Restore focus to the last saved element
         */
        restoreFocus: function() {
            if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
                lastFocusedElement.focus();
            }
        },
        
        /**
         * Go back in focus history
         */
        backFocus: function() {
            const previousElement = focusHistory.pop();
            if (previousElement && typeof previousElement.focus === 'function') {
                previousElement.focus();
                lastFocusedElement = previousElement;
            }
        },
        
        /**
         * Create a focus trap for modals and dialogs
         * @param {Element} container - Container element to trap focus within
         * @returns {Object} Focus trap controller
         */
        createFocusTrap: function(container) {
            // Find all focusable elements
            const focusableElements = container.querySelectorAll(
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
            );
            
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];
            
            // Save current focus
            this.saveFocus();
            
            // Focus first element
            if (firstElement) {
                firstElement.focus();
            }
            
            // Create event listeners
            const handleKeydown = function(event) {
                // Handle Tab key
                if (event.key === 'Tab') {
                    if (event.shiftKey && document.activeElement === firstElement) {
                        // Shift+Tab on first element -> move to last
                        event.preventDefault();
                        lastElement.focus();
                    } else if (!event.shiftKey && document.activeElement === lastElement) {
                        // Tab on last element -> move to first
                        event.preventDefault();
                        firstElement.focus();
                    }
                }
                
                // Handle Escape key
                if (event.key === 'Escape') {
                    trap.deactivate();
                }
            };
            
            // Add event listener
            container.addEventListener('keydown', handleKeydown);
            
            // Create trap controller
            const trap = {
                activate: function() {
                    // Deactivate any existing trap
                    if (activeFocusTrap) {
                        activeFocusTrap.deactivate();
                    }
                    
                    // Set as active trap
                    activeFocusTrap = trap;
                    
                    // Focus first element
                    if (firstElement) {
                        firstElement.focus();
                    }
                },
                
                deactivate: function() {
                    // Remove event listener
                    container.removeEventListener('keydown', handleKeydown);
                    
                    // Clear active trap
                    if (activeFocusTrap === trap) {
                        activeFocusTrap = null;
                    }
                    
                    // Restore focus
                    Accessibility.restoreFocus();
                }
            };
            
            // Activate trap
            trap.activate();
            
            return trap;
        },
        
        /**
         * Add proper ARIA attributes to an element
         * @param {Element} element - Element to enhance
         * @param {Object} attributes - ARIA attributes to add
         */
        enhanceWithAria: function(element, attributes) {
            if (!element) return;
            
            // Add ARIA attributes
            Object.keys(attributes).forEach(key => {
                const attrName = key.startsWith('aria') ? key : `aria-${key}`;
                element.setAttribute(attrName, attributes[key]);
            });
        },
        
        /**
         * Create a live region for announcements
         * @param {string} politeness - Politeness level ('polite' or 'assertive')
         * @returns {Element} The live region element
         */
        createLiveRegion: function(politeness = 'polite') {
            const region = document.createElement('div');
            region.setAttribute('aria-live', politeness);
            region.setAttribute('aria-atomic', 'true');
            region.setAttribute('class', 'sr-only');
            document.body.appendChild(region);
            
            return region;
        },
        
        /**
         * Announce a message to screen readers
         * @param {string} message - Message to announce
         * @param {string} politeness - Politeness level ('polite' or 'assertive')
         */
        announce: function(message, politeness = 'polite') {
            // Create or get live region
            let region = document.querySelector(`.sr-only[aria-live="${politeness}"]`);
            
            if (!region) {
                region = this.createLiveRegion(politeness);
            }
            
            // Set message
            region.textContent = '';
            
            // Use setTimeout to ensure the change is announced
            setTimeout(() => {
                region.textContent = message;
            }, 50);
        },
        
        /**
         * Add skip link for keyboard navigation
         * @param {string} targetId - ID of the element to skip to
         * @param {string} text - Text for the skip link
         */
        addSkipLink: function(targetId, text = 'Skip to main content') {
            // Check if skip link already exists
            if (document.querySelector('.skip-link')) {
                return;
            }
            
            // Create skip link
            const skipLink = document.createElement('a');
            skipLink.href = `#${targetId}`;
            skipLink.className = 'skip-link';
            skipLink.textContent = text;
            
            // Add to document
            document.body.insertBefore(skipLink, document.body.firstChild);
            
            // Add styles if not already present
            if (!document.querySelector('style#skip-link-styles')) {
                const style = document.createElement('style');
                style.id = 'skip-link-styles';
                style.textContent = `
                    .skip-link {
                        position: absolute;
                        top: -40px;
                        left: 0;
                        padding: 8px;
                        background: #1772F6;
                        color: white;
                        z-index: 1000;
                        transition: top 0.2s;
                    }
                    
                    .skip-link:focus {
                        top: 0;
                    }
                    
                    .sr-only {
                        position: absolute;
                        width: 1px;
                        height: 1px;
                        padding: 0;
                        margin: -1px;
                        overflow: hidden;
                        clip: rect(0, 0, 0, 0);
                        white-space: nowrap;
                        border: 0;
                    }
                `;
                document.head.appendChild(style);
            }
        },
        
        /**
         * Check if an element is visible and focusable
         * @param {Element} element - Element to check
         * @returns {boolean} Whether the element is focusable
         */
        isFocusable: function(element) {
            // Check if element exists
            if (!element) return false;
            
            // Check if element is visible
            const style = window.getComputedStyle(element);
            if (style.display === 'none' || style.visibility === 'hidden') {
                return false;
            }
            
            // Check if element is focusable
            const focusableTags = ['a', 'button', 'input', 'select', 'textarea'];
            const tagName = element.tagName.toLowerCase();
            
            if (focusableTags.includes(tagName)) {
                return !element.disabled;
            }
            
            // Check tabindex
            const tabIndex = element.getAttribute('tabindex');
            return tabIndex !== null && tabIndex !== '-1';
        },
        
        /**
         * Get all focusable elements within a container
         * @param {Element} container - Container element
         * @returns {Array} Array of focusable elements
         */
        getFocusableElements: function(container) {
            const elements = container.querySelectorAll(
                'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
            );
            
            return Array.from(elements).filter(element => this.isFocusable(element));
        },
        
        /**
         * Check if the current color contrast meets WCAG standards
         * @param {string} foreground - Foreground color (hex, rgb, or rgba)
         * @param {string} background - Background color (hex, rgb, or rgba)
         * @param {string} level - WCAG level ('AA' or 'AAA')
         * @param {string} size - Text size ('normal' or 'large')
         * @returns {boolean} Whether the contrast meets the standard
         */
        checkContrast: function(foreground, background, level = 'AA', size = 'normal') {
            // Convert colors to RGB
            const getRGB = function(color) {
                // Handle hex
                if (color.startsWith('#')) {
                    const hex = color.slice(1);
                    const r = parseInt(hex.slice(0, 2), 16);
                    const g = parseInt(hex.slice(2, 4), 16);
                    const b = parseInt(hex.slice(4, 6), 16);
                    return [r, g, b];
                }
                
                // Handle rgb/rgba
                if (color.startsWith('rgb')) {
                    const values = color.match(/\d+/g);
                    return [
                        parseInt(values[0], 10),
                        parseInt(values[1], 10),
                        parseInt(values[2], 10)
                    ];
                }
                
                // Default
                return [0, 0, 0];
            };
            
            // Calculate relative luminance
            const getLuminance = function(rgb) {
                const [r, g, b] = rgb.map(value => {
                    value = value / 255;
                    return value <= 0.03928
                        ? value / 12.92
                        : Math.pow((value + 0.055) / 1.055, 2.4);
                });
                
                return 0.2126 * r + 0.7152 * g + 0.0722 * b;
            };
            
            // Calculate contrast ratio
            const foreRGB = getRGB(foreground);
            const backRGB = getRGB(background);
            
            const foreL = getLuminance(foreRGB);
            const backL = getLuminance(backRGB);
            
            const ratio = (Math.max(foreL, backL) + 0.05) / (Math.min(foreL, backL) + 0.05);
            
            // Check against WCAG standards
            if (level === 'AAA') {
                return size === 'large' ? ratio >= 4.5 : ratio >= 7;
            }
            
            return size === 'large' ? ratio >= 3 : ratio >= 4.5;
        }
    };
})();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Accessibility;
} else {
    window.Accessibility = Accessibility;
}

