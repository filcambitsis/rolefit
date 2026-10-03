# Retention and account isolation

Original uploads are read with a 5 MB cap and closed in a finally block on both success and failure. The temporary upload is removed when closed. No original file is copied into application storage. Text and verified evidence are retained in the application database for matching. Uploading another CV replaces the prior CV and cascades its evidence deletion.

Every CV query and mutation is scoped to the Supabase UUID established by a verified RS256/ES256 token. Application data is in our own database. Supabase handles authentication only. Production rejects development authentication. Never expose a DEV_AUTH server outside loopback or a trusted local container network.

LLM CV cache entries are scoped by user ID and content hash; no cross-user cache reuse. Deleting a CV removes its raw text, evidence and user-scoped extraction cache. Account-data deletion also removes saved/skipped decisions and preferences. Supabase account deletion is an independent identity-provider operation.

The browser demo keeps pasted CV text only in memory. It stores only sample saved-job IDs and preferences in local storage. Browser refresh discards the CV text. Public fixtures must be explicitly anonymized and approved; the eight draft profiles are synthetic examples and do not count as study personas.

Production operators must document database backup retention and purge periods before accepting real CVs. Do not log upload bodies, bearer tokens or provider keys. Configure a request-body limit at the reverse proxy as well as the application file-size guard. If model extraction is enabled, CV text is sent to the configured model provider; disclose that provider and its retention terms to users before launch.
