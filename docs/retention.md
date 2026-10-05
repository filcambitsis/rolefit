# Retention and account isolation

Uploads have a 5 MB limit. Original files are closed and discarded after parsing, including on failure. The database retains extracted text and exact evidence passages for matching. Uploading a replacement CV deletes the previous CV and its evidence. Deleting a CV removes both; deleting account data also removes preferences and bookmarks. Supabase identity deletion remains a separate operation.

All CV queries and mutations are scoped to the authenticated user. Production uses verified Supabase JWTs; local development access is restricted to loopback peers, localhost URLs and local origins. Do not expose development authentication publicly.

Extraction and matching are rules-based and make no model-provider calls. The cleanup migration removes the old model-output cache and budget tables, including any legacy CV quotations stored there. Backups made before cleanup may still contain them.

The standalone demo contains only fixed fictional data. It accepts no personal CV uploads and stores only preferences and saved demo-job IDs in browser local storage.

Before public deployment, define database backup retention and deletion procedures, configure request-size limits, and verify authentication and account isolation in the deployed environment. Never commit private CVs, database copies, credentials or logs containing uploaded text.
