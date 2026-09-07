# Facebook and Instagram live setup

CLOUT supports Facebook Page video delivery and Instagram professional-account
Reels delivery through separate adapters. Both are disabled by default, even
when credentials exist. This lets you complete Meta configuration and review
without exposing an incomplete integration to users.

## Before enabling either platform

1. Create or select a Meta app owned by your business in the Meta for
   Developers dashboard.
2. Add yourself and every test account as an app role (administrator,
   developer, or tester) while the app is in development mode.
3. Add your production callback URLs exactly as shown below. Do not add a
   trailing slash and do not use the Render API URL as a callback.
4. Keep the app in development mode until testing succeeds. Public use needs
   Meta App Review and any required business verification.

## Facebook Page connection

1. Add the Facebook Login / Pages use case to the Meta app and configure the
   Pages permissions required by CLOUT: `pages_show_list`,
   `pages_manage_posts`, and `pages_read_engagement`.
2. In the Facebook Login settings, add this Valid OAuth Redirect URI:

   ```text
   https://clout-platform-two.vercel.app/social/callback/facebook
   ```

3. The person connecting must manage at least one Facebook Page and be an app
   role while the Meta app is in development mode.
4. Copy the Meta App ID and App Secret into Render, then set:

   ```text
   META_APP_ID=<Meta App ID>
   META_APP_SECRET=<Meta App Secret>
   FACEBOOK_LIVE_ENABLED=true
   SOCIAL_OAUTH_MODE=live
   ```

## Instagram professional-account connection

1. Add the **Instagram API with Instagram Login** product/use case to the
   Meta app. The account that connects must be an Instagram Professional
   account (Business or Creator), not a personal account.
2. Configure this redirect URI in that product's OAuth settings:

   ```text
   https://clout-platform-two.vercel.app/social/callback/instagram
   ```

3. Request the permissions CLOUT uses:
   `instagram_business_basic`, `instagram_business_content_publish`, and
   `instagram_business_manage_comments`.
4. In Render, set the Instagram Login credentials and enable only after your
   test account succeeds:

   ```text
   INSTAGRAM_APP_ID=<Instagram Login App ID>
   INSTAGRAM_APP_SECRET=<Instagram Login App Secret>
   INSTAGRAM_LIVE_ENABLED=true
   SOCIAL_OAUTH_MODE=live
   ```

The Instagram credentials can belong to the same Meta app as Facebook only if
that app has the Instagram Login product configured. CLOUT keeps the variables
separate so the two integrations can be activated and reviewed independently.

## Local testing callbacks

Add these only when testing locally with the frontend running on port 3002:

```text
http://localhost:3002/social/callback/facebook
http://localhost:3002/social/callback/instagram
```

## Safe activation checklist

- Deploy Render after saving the variables.
- Sign in to CLOUT again before connecting an account, so the browser has a
  current secure session cookie.
- Open **Connected accounts** and verify that Facebook or Instagram says
  **Automatic publishing available** before treating it as live.
- Connect an isolated test Page or Professional account first.
- Request Meta App Review before allowing people outside your app roles to
  connect or publish.

