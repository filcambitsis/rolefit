FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY pyproject.toml ./
COPY api ./api
COPY ml ./ml
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY data ./data
COPY scripts ./scripts
RUN mkdir -p work && useradd --create-home rolefit && chown -R rolefit:rolefit /app
USER rolefit
EXPOSE 8000
CMD ["uvicorn", "rolefit.main:app", "--host", "0.0.0.0", "--port", "8000"]
