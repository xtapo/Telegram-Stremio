FROM ghcr.io/astral-sh/uv:debian-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LANG=en_US.UTF-8
ENV UV_PYTHON=3.11
ENV PATH="/app/.venv/bin:$PATH"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        bash \
        git \
        curl \
        ffmpeg \
        xz-utils \
        pkg-config \
        libasound2-dev \
        ca-certificates \
        locales && \
    locale-gen en_US.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

# Debian's 7zip/p7zip packages omit the non-free RAR decoder. Use the
# official standalone release, pinned with the upstream asset SHA-256.
RUN set -eux; \
    case "$(dpkg --print-architecture)" in \
        amd64) sevenzip_arch=x64; sevenzip_sha=dc99eff5008f1ab79bd7084c68513701547a808a89502bf4133683535ab3c695 ;; \
        arm64) sevenzip_arch=arm64; sevenzip_sha=2389ba20e4d8295e8709c20b6263b69bd1ec4972fe38a04ad7a1badbf595b996 ;; \
        *) echo "Unsupported architecture for bundled 7-Zip" >&2; exit 1 ;; \
    esac; \
    curl -fsSL --retry 3 --connect-timeout 15 --max-time 120 \
        "https://github.com/ip7z/7zip/releases/download/26.03/7z2603-linux-${sevenzip_arch}.tar.xz" \
        -o /tmp/7zip.tar.xz; \
    echo "${sevenzip_sha}  /tmp/7zip.tar.xz" | sha256sum -c -; \
    mkdir /tmp/7zip; \
    tar -xJf /tmp/7zip.tar.xz -C /tmp/7zip; \
    install -m 0755 /tmp/7zip/7zz /usr/local/bin/7zz; \
    mkdir -p /usr/local/share/doc/7zip; \
    cp /tmp/7zip/License.txt /usr/local/share/doc/7zip/; \
    7zz i > /tmp/7zip-formats.txt; \
    grep -q ' Rar5 ' /tmp/7zip-formats.txt; \
    rm -rf /tmp/7zip /tmp/7zip.tar.xz /tmp/7zip-formats.txt

WORKDIR /app
COPY .python-version pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen
RUN chmod +x start.sh
CMD ["bash", "start.sh"]
