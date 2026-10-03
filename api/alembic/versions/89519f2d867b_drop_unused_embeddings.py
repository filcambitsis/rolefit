"""Drop unused embedding columns

Matching uses requirement coverage with a BM25 tiebreaker, so the
experimental embedding vectors are no longer read or written.
"""

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

revision = "89519f2d867b"
down_revision = "b7147e77d201"
branch_labels = None
depends_on = None

TABLES = ["evidence", "jobs", "requirements"]


def upgrade():
    for table in TABLES:
        # Batch mode lets SQLite drop columns by rebuilding the table.
        with op.batch_alter_table(table) as batch:
            batch.drop_column("embedding")


def downgrade():
    for table in TABLES:
        with op.batch_alter_table(table) as batch:
            batch.add_column(
                sa.Column(
                    "embedding",
                    sa.JSON().with_variant(pgvector.sqlalchemy.vector.VECTOR(dim=768), "postgresql"),
                    nullable=True,
                )
            )
