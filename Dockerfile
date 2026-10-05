FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.8.13

WORKDIR /code

COPY ./pyproject.toml ./README.md ./uv.lock* ./
COPY ./app ./app
COPY ./demo_data ./demo_data
COPY ./assets ./assets
COPY ./fleetflow_executive_presentation.html ./fleetflow_executive_presentation.html

RUN uv sync --no-dev

ARG AGENT_VERSION=0.2.0
ENV AGENT_VERSION=${AGENT_VERSION}
ENV PORT=8080
ENV GOOGLE_GENAI_USE_VERTEXAI=true
ENV LOADPILOT_BQ_PROJECT=zuhaibp-ai
ENV LOADPILOT_BQ_DATASET=loadpilot_demo

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "app.fast_api_app:app", "--host", "0.0.0.0", "--port", "8080"]
