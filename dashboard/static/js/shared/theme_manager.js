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
        density: 'normal' // compact, normal, comfortable
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
            '--toast-bg': '#ffffff'
        },
        dark: {
            '--bg-primary': '#212529',
            '--bg-secondary': '#343a40',
            '--bg-tertiary': '#495057',
            '--text-primary': '#f8f9fa',
            '--text-secondary': '#adb5bd',
            '--border-color': '#495057',
            '--accent-color': '#007bff',
            '--accent-hover': '#0069d9',
            '--sidebar-bg': '#121416',
            '--sidebar-text': '#f8f9fa',
            '--card-bg': '#343a40',
            '--card-border': '#495057',
            '--input-bg': '#343a40',
            '--input-border': '#495057',
            '--input-text': '#e9ecef',
            '--table-header-bg': '#343a40',
            '--table-row-hover': 'rgba(0, 123, 255, 0.1)',
            '--modal-bg': '#343a40',
            '--toast-bg': '#343a40'
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
        
        // Apply theme variables (light or dark)
        const themeVars = settings.darkMode ? themeVariables.dark : themeVariables.light;
        Object.entries(themeVars).forEach(([key, value]) => {
            root.style.setProperty(key, value);
        });
        
        // Apply accent color
        const accentVars = accentColors[settings.colorAccent] || accentColors.blue;
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
        
        // Dispatch theme change event
        if (window.EventBus) {
            window.EventBus.emit(window.EVENTS.UI_THEME_CHANGED, { ...settings });
        }
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
            // Check for system preference
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                settings.darkMode = true;
            }
        }
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
            }
            
            // Add theme toggle button if it doesn't exist
            if (!document.getElementById('theme-toggle')) {
                const navbar = document.querySelector('.navbar-nav');
                if (navbar) {
                    const themeToggle = document.createElement('li');
                    themeToggle.className = 'nav-item ms-2';
                    themeToggle.innerHTML = `
                        <button id="theme-toggle" class="btn btn-outline-light btn-sm">
                            <i class="bi ${settings.darkMode ? 'bi-sun' : 'bi-moon'}"></i>
                        </button>
                    `;
                    navbar.appendChild(themeToggle);
                    
                    document.getElementById('theme-toggle').addEventListener('click', () => {
                        this.toggleDarkMode();
                    });
                }
            }
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
            
            // Update theme toggle button
            const themeToggle = document.getElementById('theme-toggle');
            if (themeToggle) {
                themeToggle.innerHTML = `<i class="bi ${enabled ? 'bi-sun' : 'bi-moon'}"></i>`;
            }
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
                density: 'normal'
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

