FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860

WORKDIR /app
RUN useradd --create-home --uid 1000 user \
    && mkdir -p /app/reports /app/benchmarks/uploads \
    && chown -R user:user /app

COPY --chown=1000:1000 app ./app
COPY --chown=1000:1000 benchmarks/support_sessions.jsonl ./benchmarks/support_sessions.jsonl
COPY --chown=1000:1000 benchmarks/support_failures.jsonl ./benchmarks/support_failures.jsonl

USER 1000
EXPOSE 7860
CMD ["python", "-m", "app.space_server"]
