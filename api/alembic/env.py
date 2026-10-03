from alembic import context
from sqlalchemy import create_engine
from rolefit.config import settings
from rolefit.db import Base
from rolefit import models  # noqa: F401


def include_object(obj, name, type_, reflected, compare_to):
    return name not in {"search_vector", "ix_jobs_search_vector"}


if context.is_offline_mode():
    context.configure(
        url=settings().database_url,
        target_metadata=Base.metadata,
        literal_binds=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with create_engine(settings().database_url).connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()
