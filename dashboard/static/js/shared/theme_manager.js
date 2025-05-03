/**
 * Theme Manager - Manages application themes and appearance
 * 
 * This module provides functionality for managing the application's
 * visual theme, including dark mode and other appearance settings.
 */

const ThemeManager = (function() {
    // Theme settings
    const settings = {
        darkMode: false,
        fontSize: 'medium', // small, medium, large
        colorAccent: 'blue', // blue, green, purple, orange
        density: 'normal', // compact, normal, comfortable
        highContrast: false, // high contrast mode
        reducedMotion: false // reduced motion mode
    };
    
    // CSS variables for themes
    const themeVariables = {
        light: {
            '--bg-primary': '#ffffff',
            '--bg-secondary': '#f8f9fa',
            '--bg-tertiary': '#e9ecef',
            '--text-primary': '#212529',
            '--text-secondary': '#6c757d',
            '--border-color': '#dee2e6',
            '--accent-color': '#007bff',
            '--accent-hover': '#0069d9',
            '--sidebar-bg': '#343a40',
            '--sidebar-text': '#ffffff',
            '--card-bg': '#ffffff',
            '--card-border': '#dee2e6',
            '--input-bg': '#ffffff',
            '--input-border': '#ced4da',
            '--input-text': '#495057',
            '--table-header-bg': '#f8f9fa',
            '--table-row-hover': 'rgba(0, 123, 255, 0.05)',
            '--modal-bg': '#ffffff',
            '--toast-bg': '#ffffff',
            '--focus-outline': '#007bff',
            '--focus-outline-rgb': '0, 123, 255'
        },
        dark: {
            '--bg-primary': '#212529',
            '--bg-secondary': '#343a40',
            '--bg-tertiary': '#495057',
            '--text-primary': '#f8f9fa',
            '--text-secondary': '#adb5bd',
            '--border-color': '#495057',
            '--accent-color': '#0d6efd', // Brighter blue for better contrast in dark mode
            '--accent-hover': '#0b5ed7',
            '--sidebar-bg': '#121416',
            '--sidebar-text': '#f8f9fa',
            '--card-bg': '#343a40',
            '--card-border': '#495057',
            '--input-bg': '#343a40',
            '--input-border': '#495057',
            '--input-text': '#e9ecef',
            '--table-header-bg': '#343a40',
            '--table-row-hover': 'rgba(13, 110, 253, 0.1)', // Brighter blue for better contrast
            '--modal-bg': '#343a40',
            '--toast-bg': '#343a40',
            '--focus-outline': '#0d6efd',
            '--focus-outline-rgb': '13, 110, 253'
        },
        highContrastLight: {
            '--bg-primary': '#ffffff',
            '--bg-secondary': '#f8f9fa',
            '--bg-tertiary': '#e9ecef',
            '--text-primary': '#000000',
            '--text-secondary': '#333333',
            '--border-color': '#000000',
            '--accent-color': '#0000cc', // Darker blue for higher contrast
            '--accent-hover': '#000099',
            '--sidebar-bg': '#000000',
            '--sidebar-text': '#ffffff',
            '--card-bg': '#ffffff',
            '--card-border': '#000000',
            '--input-bg': '#ffffff',
            '--input-border': '#000000',
            '--input-text': '#000000',
            '--table-header-bg': '#f8f9fa',
            '--table-row-hover': 'rgba(0, 0, 204, 0.1)',
            '--modal-bg': '#ffffff',
            '--toast-bg': '#ffffff',
            '--focus-outline': '#0000cc',
            '--focus-outline-rgb': '0, 0, 204'
        },
        highContrastDark: {
            '--bg-primary': '#000000',
            '--bg-secondary': '#121212',
            '--bg-tertiary': '#1e1e1e',
            '--text-primary': '#ffffff',
            '--text-secondary': '#cccccc',
            '--border-color': '#ffffff',
            '--accent-color': '#4d94ff', // Brighter blue for higher contrast in dark mode
            '--accent-hover': '#3385ff',
            '--sidebar-bg': '#000000',
            '--sidebar-text': '#ffffff',
            '--card-bg': '#121212',
            '--card-border': '#ffffff',
            '--input-bg': '#121212',
            '--input-border': '#ffffff',
            '--input-text': '#ffffff',
            '--table-header-bg': '#121212',
            '--table-row-hover': 'rgba(77, 148, 255, 0.2)',
            '--modal-bg': '#121212',
            '--toast-bg': '#121212',
            '--focus-outline': '#4d94ff',
            '--focus-outline-rgb': '77, 148, 255'
        }
    };
    
    // Accent color variables
    const accentColors = {
        blue: {
            '--accent-color': '#007bff',
            '--accent-hover': '#0069d9'
        },
        green: {
            '--accent-color': '#28a745',
            '--accent-hover': '#218838'
        },
        purple: {
            '--accent-color': '#6f42c1',
            '--accent-hover': '#5e37a6'
        },
        orange: {
            '--accent-color': '#fd7e14',
            '--accent-hover': '#e96b02'
        }
    };
    
    // High contrast accent colors
    const highContrastAccentColors = {
        blue: {
            '--accent-color': '#0000cc',
            '--accent-hover': '#000099'
        },
        green: {
            '--accent-color': '#006600',
            '--accent-hover': '#004d00'
        },
        purple: {
            '--accent-color': '#5c00a3',
            '--accent-hover': '#4b0082'
        },
        orange: {
            '--accent-color': '#cc5500',
            '--accent-hover': '#b34700'
        }
    };
    
    // Font size variables
    const fontSizes = {
        small: {
            '--font-size-base': '0.875rem',
            '--font-size-lg': '1rem',
            '--font-size-sm': '0.75rem',
            '--font-size-xs': '0.7rem',
            '--heading-1': '1.75rem',
            '--heading-2': '1.5rem',
            '--heading-3': '1.25rem',
            '--heading-4': '1rem',
            '--heading-5': '0.875rem',
            '--heading-6': '0.75rem'
        },
        medium: {
            '--font-size-base': '1rem',
            '--font-size-lg': '1.25rem',
            '--font-size-sm': '0.875rem',
            '--font-size-xs': '0.75rem',
            '--heading-1': '2rem',
            '--heading-2': '1.75rem',
            '--heading-3': '1.5rem',
            '--heading-4': '1.25rem',
            '--heading-5': '1rem',
            '--heading-6': '0.875rem'
        },
        large: {
            '--font-size-base': '1.125rem',
            '--font-size-lg': '1.375rem',
            '--font-size-sm': '1rem',
            '--font-size-xs': '0.875rem',
            '--heading-1': '2.25rem',
            '--heading-2': '2rem',
            '--heading-3': '1.75rem',
            '--heading-4': '1.5rem',
            '--heading-5': '1.25rem',
            '--heading-6': '1.125rem'
        }
    };
    
    // Density variables
    const densities = {
        compact: {
            '--spacing-unit': '0.5rem',
            '--padding-sm': '0.25rem',
            '--padding-md': '0.5rem',
            '--padding-lg': '0.75rem',
            '--margin-sm': '0.25rem',
            '--margin-md': '0.5rem',
            '--margin-lg': '0.75rem',
            '--border-radius': '0.25rem'
        },
        normal: {
            '--spacing-unit': '1rem',
            '--padding-sm': '0.5rem',
            '--padding-md': '1rem',
            '--padding-lg': '1.5rem',
            '--margin-sm': '0.5rem',
            '--margin-md': '1rem',
            '--margin-lg': '1.5rem',
            '--border-radius': '0.375rem'
        },
        comfortable: {
            '--spacing-unit': '1.5rem',
            '--padding-sm': '0.75rem',
            '--padding-md': '1.5rem',
            '--padding-lg': '2.25rem',
            '--margin-sm': '0.75rem',
            '--margin-md': '1.5rem',
            '--margin-lg': '2.25rem',
            '--border-radius': '0.5rem'
        }
    };
    
    // Apply CSS variables to the document
    function applyTheme() {
        const root = document.documentElement;
        
        // Determine which theme variables to use
        let themeVars;
        if (settings.highContrast) {
            themeVars = settings.darkMode ? themeVariables.highContrastDark : themeVariables.highContrastLight;
        } else {
            themeVars = settings.darkMode ? themeVariables.dark : themeVariables.light;
        }
        
        // Apply theme variables
        Object.entries(themeVars).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });
        
        // Apply accent color
        const accentVars = settings.highContrast 
            ? (highContrastAccentColors[settings.colorAccent] || highContrastAccentColors.blue)
            : (accentColors[settings.colorAccent] || accentColors.blue);
            
        Object.entries(accentVars).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });
        
        // Apply font size
        const fontVars = fontSizes[settings.fontSize] || fontSizes.medium;
        Object.entries(fontVars).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });
        
        // Apply density
        const densityVars = densities[settings.density] || densities.normal;
        Object.entries(densityVars).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });
        
        // Add or remove dark mode class
        if (settings.darkMode) {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
        
        // Add or remove high contrast class
        if (settings.highContrast) {
            document.body.classList.add('high-contrast');
        } else {
            document.body.classList.remove('high-contrast');
        }
        
        // Add or remove reduced motion class
        if (settings.reducedMotion) {
            document.body.classList.add('reduced-motion');
        } else {
            document.body.classList.remove('reduced-motion');
        }
        
        // Dispatch theme change event
        if (window.EventBus) {
            window.EventBus.emit(window.EVENTS.UI_THEME_CHANGED, { ...settings });
        }
        
        // Announce theme change to screen readers
        announceThemeChange();
    }
    
    // Announce theme change to screen readers
    function announceThemeChange() {
        let announcement = `Theme changed to ${settings.darkMode ? 'dark' : 'light'} mode`;
        
        if (settings.highContrast) {
            announcement += ' with high contrast';
        }
        
        if (settings.reducedMotion) {
            announcement += ' and reduced motion';
        }
        
        // Create or update the live region
        let liveRegion = document.getElementById('theme-change-announcement');
        if (!liveRegion) {
            liveRegion = document.createElement('div');
            liveRegion.id = 'theme-change-announcement';
            liveRegion.setAttribute('aria-live', 'polite');
            liveRegion.setAttribute('class', 'sr-only');
            document.body.appendChild(liveRegion);
        }
        
        liveRegion.textContent = announcement;
        
        // Clear the announcement after a delay
        // Calculate timeout based on announcement length (approx. 15ms per character, minimum 3000ms)
        const announcementTimeout = Math.max(3000, announcement.length * 15);
        setTimeout(() => {
            liveRegion.textContent = '';
        }, announcementTimeout);
    }
    
    // Save settings to localStorage
    function saveSettings() {
        localStorage.setItem('wiseflow_theme_settings', JSON.stringify(settings));
    }
    
    // Load settings from localStorage
    function loadSettings() {
        const savedSettings = localStorage.getItem('wiseflow_theme_settings');
        if (savedSettings) {
            try {
                const parsed = JSON.parse(savedSettings);
                Object.assign(settings, parsed);
            } catch (error) {
                console.error('Error parsing theme settings:', error);
            }
        } else {
            // Check for system preferences
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                settings.darkMode = true;
            }
            
            if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                settings.reducedMotion = true;
            }
            
            if (window.matchMedia && window.matchMedia('(prefers-contrast: more)').matches) {
                settings.highContrast = true;
            }
        }
    }
    
    // Create accessibility controls
    function createAccessibilityControls() {
        const navbar = document.querySelector('.navbar-nav');
        if (!navbar) return;
        
        // Create accessibility dropdown
        const accessibilityDropdown = document.createElement('li');
        accessibilityDropdown.className = 'nav-item dropdown ms-2';
        accessibilityDropdown.innerHTML = `
            <a class="nav-link dropdown-toggle" href="#" id="accessibilityDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                <i class="bi bi-universal-access" aria-hidden="true"></i>
                <span class="visually-hidden">Accessibility options</span>
            </a>
            <ul class="dropdown-menu dropdown-menu-end" aria-labelledby="accessibilityDropdown">
                <li>
                    <div class="dropdown-item">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="darkModeToggle" ${settings.darkMode ? 'checked' : ''}>
                            <label class="form-check-label" for="darkModeToggle">Dark Mode</label>
                        </div>
                    </div>
                </li>
                <li>
                    <div class="dropdown-item">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="highContrastToggle" ${settings.highContrast ? 'checked' : ''}>
                            <label class="form-check-label" for="highContrastToggle">High Contrast</label>
                        </div>
                    </div>
                </li>
                <li>
                    <div class="dropdown-item">
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="reducedMotionToggle" ${settings.reducedMotion ? 'checked' : ''}>
                            <label class="form-check-label" for="reducedMotionToggle">Reduced Motion</label>
                        </div>
                    </div>
                </li>
                <li><hr class="dropdown-divider"></li>
                <li>
                    <div class="dropdown-item">
                        <label for="fontSizeSelect" class="form-label">Font Size</label>
                        <select class="form-select form-select-sm" id="fontSizeSelect">
                            <option value="small" ${settings.fontSize === 'small' ? 'selected' : ''}>Small</option>
                            <option value="medium" ${settings.fontSize === 'medium' ? 'selected' : ''}>Medium</option>
                            <option value="large" ${settings.fontSize === 'large' ? 'selected' : ''}>Large</option>
                        </select>
                    </div>
                </li>
            </ul>
        `;
        
        navbar.appendChild(accessibilityDropdown);
        
        // Add event listeners
        document.getElementById('darkModeToggle').addEventListener('change', function(e) {
            ThemeManager.setDarkMode(e.target.checked);
        });
        
        document.getElementById('highContrastToggle').addEventListener('change', function(e) {
            ThemeManager.setHighContrast(e.target.checked);
        });
        
        document.getElementById('reducedMotionToggle').addEventListener('change', function(e) {
            ThemeManager.setReducedMotion(e.target.checked);
        });
        
        document.getElementById('fontSizeSelect').addEventListener('change', function(e) {
            ThemeManager.setFontSize(e.target.value);
        });
    }
    
    return {
        /**
         * Initialize the theme manager
         */
        init: function() {
            loadSettings();
            applyTheme();
            
            // Listen for system theme changes
            if (window.matchMedia) {
                window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', event => {
                    if (event.matches) {
                        this.setDarkMode(true);
                    } else {
                        this.setDarkMode(false);
                    }
                });
                
                window.matchMedia('(prefers-reduced-motion: reduce)').addEventListener('change', event => {
                    this.setReducedMotion(event.matches);
                });
                
                window.matchMedia('(prefers-contrast: more)').addEventListener('change', event => {
                    this.setHighContrast(event.matches);
                });
            }
            
            // Create accessibility controls
            createAccessibilityControls();
        },
        
        /**
         * Toggle dark mode
         */
        toggleDarkMode: function() {
            this.setDarkMode(!settings.darkMode);
        },
        
        /**
         * Set dark mode
         * @param {boolean} enabled - Whether dark mode is enabled
         */
        setDarkMode: function(enabled) {
            settings.darkMode = enabled;
            applyTheme();
            saveSettings();
        },
        
        /**
         * Set high contrast mode
         * @param {boolean} enabled - Whether high contrast mode is enabled
         */
        setHighContrast: function(enabled) {
            settings.highContrast = enabled;
            applyTheme();
            saveSettings();
        },
        
        /**
         * Set reduced motion mode
         * @param {boolean} enabled - Whether reduced motion mode is enabled
         */
        setReducedMotion: function(enabled) {
            settings.reducedMotion = enabled;
            applyTheme();
            saveSettings();
        },
        
        /**
         * Set font size
         * @param {string} size - Font size (small, medium, large)
         */
        setFontSize: function(size) {
            if (!fontSizes[size]) {
                console.error(`Invalid font size: ${size}`);
                return;
            }
            
            settings.fontSize = size;
            applyTheme();
            saveSettings();
        },
        
        /**
         * Set accent color
         * @param {string} color - Accent color (blue, green, purple, orange)
         */
        setAccentColor: function(color) {
            if (!accentColors[color]) {
                console.error(`Invalid accent color: ${color}`);
                return;
            }
            
            settings.colorAccent = color;
            applyTheme();
            saveSettings();
        },
        
        /**
         * Set UI density
         * @param {string} density - UI density (compact, normal, comfortable)
         */
        setDensity: function(density) {
            if (!densities[density]) {
                console.error(`Invalid density: ${density}`);
                return;
            }
            
            settings.density = density;
            applyTheme();
            saveSettings();
        },
        
        /**
         * Get current theme settings
         * @returns {object} Theme settings
         */
        getSettings: function() {
            return { ...settings };
        },
        
        /**
         * Reset theme settings to defaults
         */
        resetSettings: function() {
            Object.assign(settings, {
                darkMode: false,
                fontSize: 'medium',
                colorAccent: 'blue',
                density: 'normal',
                highContrast: false,
                reducedMotion: false
            });
            
            applyTheme();
            saveSettings();
        }
    };
})();

// Export ThemeManager for use in other modules
window.ThemeManager = ThemeManager;

// Initialize theme manager when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    ThemeManager.init();
});
