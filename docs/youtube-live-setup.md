# Enabling live YouTube publishing

The YouTube adapter is intentionally disabled by default. It can only publish
when `SOCIAL_OAUTH_MODE=live`, valid Google credentials exist, and the explicit
`YOUTUBE_LIVE_ENABLED=true` switch is set.

## Google Cloud configuration

1. Use the existing CLOUT Google Cloud project.
2. In **APIs & Services -> Library**, enable **YouTube Data API v3**.
3. Open **Google Auth Platform -> Clients** and edit the same Web client used
   by CLOUT's Google sign-in.
4. Add the exact redirect URI:

   ```text
   https://clout-platform-two.vercel.app/social/callback/youtube
   ```

   For local testing also add:

   ```text
   http://localhost:3002/social/callback/youtube
   ```

5. Keep the consent screen in Testing and add the intended test channel's
   Google account under **Test users**. The requested scopes are
   `youtube.upload` and `youtube.readonly`; do not request more scopes.

## Render activation

Set these variables on the backend service. Never place the secret in Vercel
or the frontend.

```text
SOCIAL_OAUTH_MODE=live
GOOGLE_CLIENT_ID=<existing Google OAuth web client ID>
GOOGLE_CLIENT_SECRET=<existing Google OAuth web client secret>
YOUTUBE_LIVE_ENABLED=true
FRONTEND_BASE_URL=https://clout-platform-two.vercel.app
```

Redeploy Render, then open **Connected accounts** in CLOUT and connect a
YouTube channel. The page must show **Automatic publishing available** before
an owner attempts a live delivery.

## Safety checks

- Test with an isolated test channel first. The current connector publishes videos as public, so do not use your primary public channel until you have verified the workflow.
- Confirm the connected channel belongs to the person pressing Share.
- CLOUT only publishes after an explicit user action; it does not schedule or
  background-post YouTube videos.
- Leave `YOUTUBE_LIVE_ENABLED=false` if Google has not approved the requested
  scopes for public users. Testing-mode Google accounts can still test the
  connection.
