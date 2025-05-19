# Authentication System Documentation

## Overview

WiseFlow uses OAuth 2.0 with JWT tokens for authentication and authorization. This system provides:

- Secure authentication using industry-standard protocols
- Role-based access control (RBAC) for fine-grained permissions
- JWT tokens with appropriate security measures
- Refresh token flow for improved user experience
- Backward compatibility with API key authentication

## Authentication Methods

### OAuth 2.0

WiseFlow supports the following OAuth 2.0 grant types:

1. **Authorization Code Flow**
   - Most secure flow for web applications
   - Requires user to authenticate and authorize the application
   - Returns an authorization code that is exchanged for tokens

2. **Password Grant**
   - For trusted first-party applications
   - User provides username and password directly to the application
   - Returns access and refresh tokens

3. **Client Credentials**
   - For machine-to-machine communication
   - Client provides client ID and secret
   - Returns access token only (no refresh token)

4. **Refresh Token**
   - Used to obtain a new access token when the current one expires
   - Requires a valid refresh token
   - Returns a new access token and optionally a new refresh token

### API Key Authentication (Legacy)

For backward compatibility, WiseFlow continues to support API key authentication:

- API key is passed in the `X-API-Key` header
- All endpoints support both OAuth and API key authentication
- API key authentication will be deprecated in the future

## Token Types

### Access Token

- JWT token used for authentication
- Contains user ID, scopes, and expiration time
- Short-lived (default: 30 minutes)
- Must be included in the `Authorization` header as a Bearer token

### Refresh Token

- Used to obtain a new access token
- Long-lived (default: 7 days)
- Stored securely in the database
- Can be revoked by the server

## Authorization

WiseFlow uses role-based access control (RBAC) for authorization:

- **Users** have one or more **Roles**
- **Roles** have one or more **Permissions**
- **Permissions** grant access to specific resources and actions

### Roles

Default roles:

- **Admin**: Full access to all resources
- **User**: Limited access to resources

### Permissions

Permissions follow the format `resource:action`:

- `users:read`: Read user data
- `users:write`: Create and update users
- `users:delete`: Delete users
- `webhooks:read`: Read webhooks
- `webhooks:write`: Create and update webhooks
- `webhooks:delete`: Delete webhooks
- `api:read`: Access API endpoints
- `api:write`: Modify data via API
- `admin:access`: Access admin features

## API Endpoints

### OAuth Endpoints

- `POST /api/v1/oauth/token`: OAuth token endpoint
- `GET /api/v1/oauth/authorize`: OAuth authorization endpoint
- `POST /api/v1/oauth/revoke`: Token revocation endpoint

### User Management

- `POST /api/v1/users`: Create a new user
- `GET /api/v1/users/me`: Get current user information
- `GET /api/v1/users/{user_id}`: Get user information by ID

### OAuth Client Management

- `POST /api/v1/oauth/clients`: Create a new OAuth client

## Usage Examples

### Web Application Flow

1. Redirect user to authorization endpoint:
   ```
   GET /api/v1/oauth/authorize?response_type=code&client_id=CLIENT_ID&redirect_uri=REDIRECT_URI&scope=read+write
   ```

2. User authenticates and authorizes the application

3. Server redirects to the redirect URI with an authorization code:
   ```
   REDIRECT_URI?code=AUTHORIZATION_CODE
   ```

4. Exchange the authorization code for tokens:
   ```
   POST /api/v1/oauth/token
   Content-Type: application/x-www-form-urlencoded
   
   grant_type=authorization_code&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&code=AUTHORIZATION_CODE&redirect_uri=REDIRECT_URI
   ```

5. Use the access token to access protected resources:
   ```
   GET /api/v1/users/me
   Authorization: Bearer ACCESS_TOKEN
   ```

### Password Grant Flow

1. Obtain tokens using username and password:
   ```
   POST /api/v1/oauth/token
   Content-Type: application/x-www-form-urlencoded
   
   grant_type=password&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&username=USERNAME&password=PASSWORD&scope=read+write
   ```

2. Use the access token to access protected resources:
   ```
   GET /api/v1/users/me
   Authorization: Bearer ACCESS_TOKEN
   ```

### Refresh Token Flow

1. Obtain a new access token using a refresh token:
   ```
   POST /api/v1/oauth/token
   Content-Type: application/x-www-form-urlencoded
   
   grant_type=refresh_token&client_id=CLIENT_ID&client_secret=CLIENT_SECRET&refresh_token=REFRESH_TOKEN
   ```

### API Key Authentication (Legacy)

```
GET /api/v1/process
X-API-Key: API_KEY
```

## Security Considerations

- All authentication endpoints must be accessed over HTTPS
- Access tokens are short-lived to minimize the impact of token theft
- Refresh tokens are stored securely and can be revoked
- Passwords are hashed using bcrypt
- Rate limiting is applied to authentication endpoints
- Failed authentication attempts are logged

## Migration from API Key to OAuth

1. Create an OAuth client for your application
2. Implement the appropriate OAuth flow
3. Update your application to use OAuth authentication
4. Continue to support API key authentication during the transition period
5. Once all clients have migrated, disable API key authentication

## Troubleshooting

### Common Errors

- `Invalid client`: Client ID or secret is incorrect
- `Invalid grant`: Grant type is not supported or parameters are missing
- `Invalid token`: Token is malformed, expired, or has been revoked
- `Insufficient scope`: Token does not have the required scope
- `Access denied`: User does not have the required permission or role

### Debugging

- Check the token expiration time
- Verify that the client ID and secret are correct
- Ensure that the redirect URI matches the one registered with the client
- Check that the user has the required permissions or roles
- Verify that the token has the required scopes

