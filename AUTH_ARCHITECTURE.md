# Authentication and user-data architecture (production design)

This starter app does **not** yet implement login or persistent per-user accounts. Do not expose it publicly as a multi-user financial app in its current form.

## Recommended architecture

- **Identity provider:** Supabase Auth (email/password or supported OAuth; enable email verification and MFA where appropriate).
- **Frontend:** use the official Supabase client to sign users in and obtain a short-lived access token.
- **Backend:** validate the access token on every protected FastAPI request. Never trust a user ID supplied in the request body.
- **Database:** PostgreSQL tables such as `profiles`, `watchlists`, `portfolio_positions`, `research_history`, `prediction_history`, and `user_alerts`.
- **Tenant isolation:** every user-owned row includes `user_id`. Enforce PostgreSQL Row Level Security (RLS), with policies restricting rows to the authenticated user. Keep service-role secrets only on the server.
- **Secrets:** use environment variables / deployment secret storage. Never commit `.env`, expose API keys to browser code, or ask users for broker passwords/OTPs in chat.
- **Audit and security:** rate-limit API calls, validate inputs, log security-relevant events without storing credentials, protect against CSRF/XSS where applicable, use HTTPS, add backups and a retention/deletion process.

## Suggested request flow

1. User signs in through Supabase Auth.
2. Browser receives an access token from the auth SDK.
3. Browser calls the FastAPI backend with the bearer token.
4. Backend verifies the token and derives the user ID from verified claims.
5. Backend reads/writes only that user's records; PostgreSQL RLS provides a second layer of isolation.
6. Provider API keys for market data or AI remain on the server.

## Before public release

Implement and test the auth flow, RLS policies, session expiry, password reset, account deletion, data export, access controls, monitoring and incident response. Have a qualified security reviewer test authorization boundaries. This document is architecture guidance, not a claim that authentication is already implemented.
