# Telegram Bot API stub — minimal image for docker-compose.test.yml.
# Runs the same Python module that pytest unit tests import directly,
# so behavior is identical between in-process tests and docker E2E.
FROM python:3.12-slim

WORKDIR /app

# aiohttp version matches the project's pinned range (^3.11.11);
# 3.12.x is in the lockfile so we align here to avoid drift.
RUN pip install --no-cache-dir 'aiohttp>=3.11,<3.13'

# Copy stub directory only — no app source needed.
COPY tests/e2e/telegram_api_stub /app/tests/e2e/telegram_api_stub

# Stub-only Python path; running via module form preserves package imports.
ENV PYTHONPATH=/app
ENV STUB_PORT=8081
EXPOSE 8081

# Healthcheck-friendly endpoint at /health.
CMD ["python", "-m", "tests.e2e.telegram_api_stub"]
