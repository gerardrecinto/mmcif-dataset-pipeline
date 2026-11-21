FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY mmcifds ./mmcifds
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home runner
USER 10001
CMD ["mmcifds", "--help"]
