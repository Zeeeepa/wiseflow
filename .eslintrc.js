module.exports = {
  "env": {
    "browser": true,
    "es2021": true
  },
  "extends": "eslint:recommended",
  "parserOptions": {
    "ecmaVersion": 12,
    "sourceType": "module"
  },
  "rules": {
    "no-unused-vars": "warn",
    "no-console": ["warn", { "allow": ["error", "warn"] }],
    "indent": ["error", 2],
    "linebreak-style": ["error", "unix"],
    "quotes": ["error", "single"],
    "semi": ["error", "always"]
  },
  "globals": {
    "window": true,
    "document": true,
    "console": true,
    "ThemeManager": true,
    "StateManager": true,
    "EventBus": true,
    "ComponentLoader": true,
    "Utils": true
  }
};

