FROM python:3.12-slim

ARG UGLYERR_REF
ARG TORCH_VERSION=2.11.0
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md process.py ./
RUN test -n "$UGLYERR_REF" \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu "torch==${TORCH_VERSION}+cpu" "torchaudio==${TORCH_VERSION}+cpu" "torchcodec==0.13.0+cpu" \
    && pip install --no-cache-dir "yt-dlp>=2025.1.15" "pyannote.audio>=3.3" \
    && pip install --no-cache-dir "git+https://github.com/smarbaa/yt-dlp-ugly-err.git@${UGLYERR_REF}"
COPY src ./src
RUN pip install --no-cache-dir --no-deps .

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "process.py"]
