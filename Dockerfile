FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    streamlit \
    pandas \
    numpy \
    pdf2docx \
    pypdf \
    langchain-openai \
    langchain-core \
    langchain-community \
    langchain-text-splitters

ENTRYPOINT [ "streamlit", "run", "/app/app.py" ]
