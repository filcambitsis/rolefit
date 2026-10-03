"""Postgres full-text indexing and exact-span database guard."""

from alembic import op

revision = "b7147e77d201"
down_revision = "80d26a1c597f"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(
        "ALTER TABLE jobs ADD COLUMN search_vector tsvector GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || description)) STORED"
    )
    op.execute("CREATE INDEX ix_jobs_search_vector ON jobs USING gin(search_vector)")
    op.execute("""CREATE FUNCTION verify_evidence_span() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE original_text text;
    BEGIN
      SELECT text INTO original_text FROM cvs WHERE id=NEW.cv_id;
      IF NEW.start < 0 OR NEW."end" <= NEW.start OR trim(NEW.quote) = '' OR
         substring(original_text FROM NEW.start+1 FOR NEW."end"-NEW.start) IS DISTINCT FROM NEW.quote THEN
        RAISE EXCEPTION 'Evidence must be an exact CV substring';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute(
        "CREATE TRIGGER evidence_span_guard BEFORE INSERT OR UPDATE ON evidence FOR EACH ROW EXECUTE FUNCTION verify_evidence_span()"
    )


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER evidence_span_guard ON evidence")
    op.execute("DROP FUNCTION verify_evidence_span()")
    op.execute("DROP INDEX ix_jobs_search_vector")
    op.execute("ALTER TABLE jobs DROP COLUMN search_vector")
