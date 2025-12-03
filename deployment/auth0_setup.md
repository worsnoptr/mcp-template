# Auth0 Authentication Setup

This guide walks through setting up Auth0 for MCP server authentication.

## Prerequisites

- Auth0 account (free tier available)
- AWS account with AgentCore access

## Step 1: Create Auth0 Application

1. Log in to [Auth0 Dashboard](https://manage.auth0.com/)
2. Navigate to **Applications** → **Applications**
3. Click **Create Application**
4. Configure application:
   - Name: `MCP Server`
   - Application Type: **Single Page Web Applications** or **Regular Web Applications**
5. Click **Create**

## Step 2: Configure Application Settings

1. In your application settings, configure:

   **Application URIs:**
   - Allowed Callback URLs: `https://yourapp.com/callback`
   - Allowed Logout URLs: `https://yourapp.com`
   - Allowed Web Origins: `https://yourapp.com`

2. **Application Properties:**
   - Token Endpoint Authentication Method: **None** (for public clients)
   - Or **Post** (for confidential clients with secret)

3. **Advanced Settings** → **OAuth:**
   - JsonWebToken Signature Algorithm: **RS256**
   - OIDC Conformant: **Enabled**

4. Save changes

## Step 3: Get Discovery URL

Your Auth0 discovery URL follows this format:

```
https://{your-domain}.auth0.com/.well-known/openid-configuration
```

Example:
```
https://myapp.us.auth0.com/.well-known/openid-configuration
```

Where `{your-domain}` is your Auth0 tenant domain found in:
- Dashboard → Settings → Domain

You can verify it works by opening it in a browser - you should see OAuth configuration JSON.

## Step 4: Note Your Credentials

From the application settings page, note:

1. **Domain**: `myapp.us.auth0.com`
2. **Client ID**: `abc123def456ghi789...`
3. **Client Secret**: (if using confidential client)

## Step 5: Configure AgentCore Deployment

When running `agentcore configure`, provide:

1. **OAuth Discovery URL**: 
   ```
   https://{your-domain}.auth0.com/.well-known/openid-configuration
   ```

2. **Client ID**: Your application's Client ID

## Step 6: Get Bearer Token for Testing

### Method 1: Using Auth0 Test Tool

1. In Auth0 Dashboard, go to your application
2. Click **Quick Start** tab
3. Follow instructions to get a test token

### Method 2: Using OAuth Password Grant (for testing only)

```bash
curl --request POST \
  --url 'https://{your-domain}.auth0.com/oauth/token' \
  --header 'content-type: application/json' \
  --data '{
    "grant_type": "password",
    "username": "user@example.com",
    "password": "password",
    "audience": "https://{your-domain}.auth0.com/api/v2/",
    "client_id": "{your-client-id}",
    "client_secret": "{your-client-secret}",
    "scope": "openid profile email"
  }'
```

Extract the `id_token` from the response:

```bash
export BEARER_TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
python tests/test_client_remote.py
```

### Method 3: Using Authorization Code Flow (recommended for production)

1. Redirect user to:
   ```
   https://{your-domain}.auth0.com/authorize?
     response_type=code&
     client_id={your-client-id}&
     redirect_uri={your-callback-url}&
     scope=openid profile email&
     state={random-state}
   ```

2. User authenticates and is redirected back with code

3. Exchange code for token:
   ```bash
   curl --request POST \
     --url 'https://{your-domain}.auth0.com/oauth/token' \
     --header 'content-type: application/json' \
     --data '{
       "grant_type": "authorization_code",
       "client_id": "{your-client-id}",
       "client_secret": "{your-client-secret}",
       "code": "{authorization-code}",
       "redirect_uri": "{your-callback-url}"
     }'
   ```

## Step 7: Create Test Users

### Using Auth0 Dashboard

1. Navigate to **User Management** → **Users**
2. Click **Create User**
3. Enter details:
   - Email: `test@example.com`
   - Password: Strong password
   - Connection: **Username-Password-Authentication**
4. Create user

### Using Auth0 Management API

```bash
curl --request POST \
  --url 'https://{your-domain}.auth0.com/api/v2/users' \
  --header 'authorization: Bearer {management-api-token}' \
  --header 'content-type: application/json' \
  --data '{
    "email": "test@example.com",
    "password": "StrongPassword123!",
    "connection": "Username-Password-Authentication",
    "email_verified": true
  }'
```

## Token Configuration

### Configure Token Lifetime

1. In Auth0 Dashboard, go to **Applications** → **APIs**
2. Select your API or create one
3. Configure **Token Settings**:
   - Token Expiration: 86400 seconds (24 hours)
   - Token Expiration For Browser Flows: 3600 seconds (1 hour)

### Custom Claims

Add custom claims to tokens using Auth0 Rules or Actions:

```javascript
// Auth0 Action example
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://your-namespace.com';
  api.idToken.setCustomClaim(`${namespace}/roles`, event.user.app_metadata.roles);
};
```

## End-to-End Flow with AgentCore

### 1. Deploy with Auth0

```bash
# Configure deployment
agentcore configure -e src/server.py --protocol MCP

# When prompted for OAuth:
# Discovery URL: https://myapp.us.auth0.com/.well-known/openid-configuration
# Client ID: your-auth0-client-id

# Deploy
agentcore launch
```

### 2. Get Token

```bash
# Using password grant (testing only)
TOKEN=$(curl -s --request POST \
  --url 'https://myapp.us.auth0.com/oauth/token' \
  --header 'content-type: application/json' \
  --data '{
    "grant_type": "password",
    "username": "test@example.com",
    "password": "YourPassword123!",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "scope": "openid profile email"
  }' | jq -r '.id_token')

export BEARER_TOKEN=$TOKEN
```

### 3. Test Remote Server

```bash
export AGENT_ARN="your-agent-runtime-arn"
python tests/test_client_remote.py
```

## Security Best Practices

1. **Use Strong Password Policies**
   - Configure in **Authentication** → **Database** → **Password Policy**
   - Require: Minimum 8 characters, uppercase, lowercase, numbers, symbols

2. **Enable Multi-Factor Authentication**
   - Navigate to **Security** → **Multi-factor Auth**
   - Enable SMS, push notifications, or TOTP

3. **Configure Anomaly Detection**
   - Enable brute force protection
   - Enable breached password detection

4. **Use Rules/Actions for Additional Security**
   - Add email verification requirement
   - Implement rate limiting
   - Add custom authorization logic

5. **Monitor Authentication Events**
   - Use Auth0 logs
   - Set up alerts for suspicious activity
   - Export logs to SIEM if needed

6. **Token Best Practices**
   - Use short-lived tokens (1 hour)
   - Implement refresh token rotation
   - Validate tokens on every request

7. **Protect Client Credentials**
   - Never expose client secrets in public repositories
   - Use environment variables or secrets manager
   - Rotate secrets regularly

## Troubleshooting

### Error: Unauthorized

**Solution:**
- Verify token is valid and not expired
- Check token is sent as: `Authorization: Bearer {token}`
- Verify discovery URL matches Auth0 tenant

### Error: Invalid audience

**Solution:**
- Configure API in Auth0
- Include audience in token request:
  ```json
  {
    "audience": "https://your-api-audience"
  }
  ```

### Error: Invalid client

**Solution:**
- Verify client ID is correct
- Check application is enabled in Auth0
- Verify application type matches usage

### Token doesn't include expected claims

**Solution:**
- Check Auth0 Rules/Actions are enabled
- Verify namespace for custom claims
- Test token at [jwt.io](https://jwt.io)

## Integration Examples

### Python Application

```python
import requests

def get_auth0_token(domain, client_id, client_secret, username, password):
    """Get Auth0 token for testing."""
    response = requests.post(
        f'https://{domain}/oauth/token',
        json={
            'grant_type': 'password',
            'username': username,
            'password': password,
            'client_id': client_id,
            'client_secret': client_secret,
            'scope': 'openid profile email'
        }
    )
    response.raise_for_status()
    return response.json()['id_token']

# Usage
token = get_auth0_token(
    domain='myapp.us.auth0.com',
    client_id='your-client-id',
    client_secret='your-client-secret',
    username='test@example.com',
    password='password'
)
```

### JavaScript Application

```javascript
const getAuth0Token = async (domain, clientId, clientSecret, username, password) => {
  const response = await fetch(`https://${domain}/oauth/token`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      grant_type: 'password',
      username,
      password,
      client_id: clientId,
      client_secret: clientSecret,
      scope: 'openid profile email'
    })
  });
  
  const data = await response.json();
  return data.id_token;
};
```

## Additional Resources

- [Auth0 Documentation](https://auth0.com/docs)
- [Auth0 Quickstarts](https://auth0.com/docs/quickstarts)
- [OAuth 2.0 Best Practices](https://oauth.net/2/best-practices/)
- [JWT Debugger](https://jwt.io/)
