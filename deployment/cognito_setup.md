# Amazon Cognito Authentication Setup

This guide walks through setting up Amazon Cognito for MCP server authentication.

## Prerequisites

- AWS account with appropriate permissions
- AWS CLI configured

## Step 1: Create Cognito User Pool

### Using AWS Console

1. Navigate to Amazon Cognito in the AWS Console
2. Click **Create user pool**
3. Configure sign-in experience:
   - Sign-in options: **Email**
   - Provider type: **Cognito user pool**
4. Configure security requirements:
   - Password policy: Choose your requirements
   - Multi-factor authentication: **Optional** (recommended: Optional or Required)
5. Configure sign-up experience:
   - Self-service sign-up: **Enable**
   - Required attributes: **Email**
6. Configure message delivery:
   - Email provider: **Send email with Cognito**
7. Integrate your app:
   - User pool name: `mcp-server-users`
   - App client name: `mcp-server-client`
   - App type: **Public client**
8. Review and create

### Using AWS CLI

```bash
# Create user pool
aws cognito-idp create-user-pool \
    --pool-name mcp-server-users \
    --auto-verified-attributes email \
    --policies "PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true}" \
    --region us-west-2

# Note the UserPoolId from the output
USER_POOL_ID="us-west-2_XXXXXXXXX"

# Create app client
aws cognito-idp create-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-name mcp-server-client \
    --no-generate-secret \
    --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH \
    --region us-west-2

# Note the ClientId from the output
CLIENT_ID="xxxxxxxxxxxxxxxxxxxxx"
```

## Step 2: Configure OAuth Settings

### Using AWS Console

1. In your user pool, go to **App integration** tab
2. Click on your app client
3. Edit **Hosted UI settings**:
   - Callback URLs: `https://yourapp.com/callback`
   - Sign out URLs: `https://yourapp.com/signout`
   - Allowed OAuth flows: **Authorization code grant**, **Implicit grant**
   - Allowed OAuth scopes: **openid**, **email**, **profile**
4. Save changes

### Using AWS CLI

```bash
aws cognito-idp update-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-id $CLIENT_ID \
    --allowed-o-auth-flows authorization_code implicit \
    --allowed-o-auth-scopes openid email profile \
    --allowed-o-auth-flows-user-pool-client \
    --callback-urls https://yourapp.com/callback \
    --logout-urls https://yourapp.com/signout \
    --region us-west-2
```

## Step 3: Get Discovery URL

The discovery URL is needed for AgentCore deployment:

```
https://cognito-idp.{region}.amazonaws.com/{userPoolId}/.well-known/openid-configuration
```

Example:
```
https://cognito-idp.us-west-2.amazonaws.com/us-west-2_123456789/.well-known/openid-configuration
```

You can verify it's working by opening it in a browser - you should see a JSON document with OAuth configuration.

## Step 4: Create Test User

### Using AWS Console

1. In your user pool, go to **Users** tab
2. Click **Create user**
3. Enter user details:
   - Email: `test@example.com`
   - Temporary password: Generate or specify
4. Create user

### Using AWS CLI

```bash
aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username test@example.com \
    --user-attributes Name=email,Value=test@example.com Name=email_verified,Value=true \
    --temporary-password TempPassword123! \
    --region us-west-2
```

## Step 5: Configure AgentCore Deployment

When running `agentcore configure`, provide:

1. **OAuth Discovery URL**: 
   ```
   https://cognito-idp.{region}.amazonaws.com/{userPoolId}/.well-known/openid-configuration
   ```

2. **Client ID**: The app client ID from Step 1

## Step 6: Get Bearer Token for Testing

### Using AWS CLI

```bash
# Authenticate and get tokens
aws cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id $CLIENT_ID \
    --auth-parameters USERNAME=test@example.com,PASSWORD=YourPassword123! \
    --region us-west-2

# Extract the IdToken from the output
BEARER_TOKEN="eyJraWQiOiI..."

# Use the token for testing
export BEARER_TOKEN=$BEARER_TOKEN
python tests/test_client_remote.py
```

### Using Hosted UI

1. Get the hosted UI URL:
   ```
   https://{domain}.auth.{region}.amazoncognito.com/login?client_id={clientId}&response_type=token&scope=openid+email+profile&redirect_uri={redirectUri}
   ```

2. Open in browser and sign in

3. Extract the `id_token` from the redirect URL

## Token Management

### Token Lifetime

By default, Cognito tokens expire after:
- ID token: 1 hour
- Access token: 1 hour
- Refresh token: 30 days

### Refresh Token

```bash
aws cognito-idp initiate-auth \
    --auth-flow REFRESH_TOKEN_AUTH \
    --client-id $CLIENT_ID \
    --auth-parameters REFRESH_TOKEN={refreshToken} \
    --region us-west-2
```

## Security Best Practices

1. **Use Strong Password Policies**
   - Minimum 8 characters
   - Require uppercase, lowercase, numbers, and symbols

2. **Enable MFA**
   - Strongly recommended for production
   - Supports SMS and TOTP

3. **Configure Token Expiration**
   - Set appropriate lifetimes based on your security requirements
   - Use refresh tokens for long-lived sessions

4. **Monitor Authentication Events**
   - Enable CloudWatch logging for Cognito
   - Monitor failed authentication attempts

5. **Use HTTPS Only**
   - Never send tokens over unencrypted connections

6. **Rotate Secrets**
   - Regularly rotate app client secrets if using confidential clients

## Troubleshooting

### Error: User is not confirmed

```bash
aws cognito-idp admin-confirm-sign-up \
    --user-pool-id $USER_POOL_ID \
    --username test@example.com \
    --region us-west-2
```

### Error: Invalid token

- Verify token hasn't expired
- Check token is being sent in correct format: `Bearer {token}`
- Verify discovery URL matches the user pool

### Error: Client is not configured for OAuth

- Ensure OAuth flows are enabled in app client settings
- Verify callback URLs are configured

## Additional Resources

- [Amazon Cognito Documentation](https://docs.aws.amazon.com/cognito/)
- [OAuth 2.0 Specification](https://oauth.net/2/)
- [OpenID Connect Specification](https://openid.net/connect/)
