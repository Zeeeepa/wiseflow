# Upgrading to WiseFlow 2.0

This guide provides detailed instructions for upgrading from WiseFlow 1.x to WiseFlow 2.0.

## Overview of Changes

WiseFlow 2.0 includes several major changes:

- Upgraded dependencies to their latest versions
- Migrated from Flask to FastAPI for the API server
- Enhanced security with JWT authentication and improved API key management
- Improved performance with better concurrency, caching, and resource management
- Added comprehensive metrics collection and monitoring
- Enhanced error handling and recovery strategies
- Improved LLM integration with support for multiple providers

## Step-by-Step Upgrade Guide

### 1. Backup Your Data

Before upgrading, make sure to backup your data:

```bash
# Backup PocketBase data
cp -r pb/pb_data pb/pb_data_backup

# Backup configuration
cp .env .env.backup
```

### 2. Update Dependencies

Update your dependencies to the latest versions:

```bash
pip install -r requirements.txt
```

### 3. Update Configuration

WiseFlow 2.0 introduces new configuration options. Review your `.env` file and add any missing configuration:

```bash
# Copy the example configuration
cp .env.example .env.new

# Compare with your existing configuration
diff .env .env.new

# Update your configuration
# Edit .env with any new settings
```

Key new configuration options:

- `ENABLE_MODEL_FALLBACK`: Enable automatic fallback to alternative models
- `ENABLE_CACHING`: Enable response caching
- `ENABLE_RATE_LIMITING`: Enable API rate limiting
- `ENABLE_METRICS`: Enable metrics collection
- `ENABLE_TRACING`: Enable request tracing
- `ENABLE_SECURITY`: Enable enhanced security features
- `JWT_SECRET_KEY`: Secret key for JWT authentication
- `JWT_ALGORITHM`: Algorithm for JWT authentication
- `JWT_EXPIRATION_MINUTES`: Expiration time for JWT tokens

### 4. Database Migration

Run the database migration script to update your database schema:

```bash
python scripts/migrate_schema.py
```

### 5. API Changes

If you're using the WiseFlow API, you'll need to update your clients to work with the new FastAPI endpoints.

#### Key API Changes:

1. **Authentication**:
   - API key should now be provided in the `X-API-Key` header instead of as a query parameter
   - JWT authentication is now available for more secure access

2. **Endpoints**:
   - The base path for all API endpoints is now `/api/v1/`
   - Some endpoint paths have changed for better organization

3. **Request/Response Format**:
   - All responses now include a consistent structure
   - Error responses include more detailed information

4. **New Endpoints**:
   - `/api/v1/metrics`: Get system metrics
   - `/api/v1/health`: Health check endpoint
   - `/api/v1/docs`: Interactive API documentation

### 6. Code Changes

If you've extended WiseFlow or integrated it into your codebase, you'll need to update your code to work with the new version.

#### Key Code Changes:

1. **Imports**:
   - Some modules have been moved or renamed
   - Check import statements and update as needed

2. **Configuration**:
   - Use the new configuration system from `core.config`
   - Access configuration values using `config.get()`

3. **Error Handling**:
   - Use the new error handling system from `core.utils.error_handling`
   - Custom exceptions now inherit from `WiseflowError`

4. **LLM Integration**:
   - Use the new LLM wrappers from `core.llms`
   - Support for multiple LLM providers via LiteLLM

### 7. Testing

After upgrading, thoroughly test your application to ensure everything works as expected:

```bash
# Run the test suite
python scripts/run_tests.py

# Start the application
python wiseflow.py

# Check the dashboard
# Open http://localhost:8080 in your browser
```

## Breaking Changes

### Removed Features

- The legacy API endpoints have been removed
- The old configuration system has been replaced
- Some deprecated functions have been removed

### Changed Behavior

- The default concurrency settings have been increased
- The caching system now uses Redis by default if available
- Error handling is more strict and provides more detailed information
- The dashboard has been redesigned and includes new features

## Troubleshooting

### Common Issues

1. **Missing Dependencies**:
   - If you encounter missing dependencies, run `pip install -r requirements.txt` again
   - Some dependencies may require system packages, check the error messages

2. **Configuration Errors**:
   - If you see configuration errors, check your `.env` file
   - Make sure all required configuration options are set

3. **Database Errors**:
   - If you encounter database errors, try running the migration script again
   - If that doesn't work, restore from your backup and try again

4. **API Errors**:
   - If your API clients are failing, check the API documentation
   - Update your clients to use the new endpoints and authentication methods

### Getting Help

If you encounter any issues not covered in this guide, please:

1. Check the [documentation](https://wiseflow.readthedocs.io/)
2. Open an issue on GitHub
3. Contact support at support@wiseflow.ai

## What's Next

After upgrading to WiseFlow 2.0, you can take advantage of the new features:

- Explore the new dashboard features
- Try the improved LLM integration
- Use the new metrics and monitoring capabilities
- Implement the enhanced security features

Check the [documentation](https://wiseflow.readthedocs.io/) for more information on these features.

