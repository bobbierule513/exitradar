# Secret rotation

API keys and database credentials must never be committed. `.env` is gitignored.

If a key was pasted into chat, logs, screenshots, or a ticket, treat it as **compromised** and rotate it in the provider console before deploying.

## Checklist

1. **Groq** — [console.groq.com](https://console.groq.com) → API keys → revoke the old key → create a new `GROQ_API_KEY`.
2. **Supabase** — Project Settings → API → reset `service_role` / `anon` JWT signing if those values leaked → update `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`.
3. **Database password** — Project Settings → Database → reset password → set `DATABASE_URL`. URL-encode reserved characters (`@` → `%40`).
4. **Google Places / OpenAI / Anthropic** — rotate any key that left the secrets manager.
5. Redeploy Cloud Run / Vercel with the new secret values (never bake keys into images).

Do not paste replacement keys into GitHub issues, PRs, or chat.
