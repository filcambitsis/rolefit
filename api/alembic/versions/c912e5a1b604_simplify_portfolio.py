"""Remove model-extraction storage, unused search indexing and skipped decisions.

Downgrade recreates empty retired tables; deleted caches and skips are not restored.
Earlier revision IDs remain valid. Historical embedding placeholders use JSON on
fresh installs, so running the migration chain no longer requires pgvector.
"""

import json

from alembic import op
import sqlalchemy as sa

revision = "c912e5a1b604"
down_revision = "89519f2d867b"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_jobs_search_vector")
        op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS search_vector")
    op.drop_table("extraction_cache")
    op.drop_table("llm_budget")
    op.execute("DELETE FROM decisions WHERE state = 'skipped'")
    aliases = {"AI Consultant", "AI Solutions & Implementation"}
    jobs = sa.table("jobs", sa.column("family", sa.String))
    connection.execute(
        jobs.update().where(jobs.c.family.in_(aliases)).values(family="AI Consulting & Solutions")
    )
    users = sa.table("users", sa.column("id", sa.String), sa.column("preferences", sa.JSON))
    for user_id, prefs in connection.execute(sa.select(users.c.id, users.c.preferences)).all():
        if isinstance(prefs, str):
            prefs = json.loads(prefs)
        prefs = dict(prefs or {})
        if "families" in prefs:
            prefs["families"] = list(
                dict.fromkeys("AI Consulting & Solutions" if f in aliases else f for f in prefs["families"])
            )
            connection.execute(users.update().where(users.c.id == user_id).values(preferences=prefs))


def downgrade():
    op.create_table(
        "extraction_cache",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("scope", sa.String(80), nullable=False),
        sa.Column("model_version", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=False),
    )
    op.create_index("ix_extraction_cache_scope", "extraction_cache", ["scope"])
    op.create_table(
        "llm_budget",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("spent_usd", sa.Float(), nullable=False),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE jobs ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || description)) STORED"
        )
        op.execute("CREATE INDEX ix_jobs_search_vector ON jobs USING gin(search_vector)")
