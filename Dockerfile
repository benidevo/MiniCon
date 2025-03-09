FROM debian:bullseye-slim

RUN apt-get update && apt-get install -y \
    curl \
    git \
    vim \
    less \
    procps \
    iproute2 \
    wget \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://www.python.org/ftp/python/3.11.7/Python-3.11.7.tgz && \
    tar -xf Python-3.11.7.tgz && \
    cd Python-3.11.7 && \
    ./configure --enable-optimizations && \
    make -j $(nproc) && \
    make altinstall && \
    cd .. && \
    rm -rf Python-3.11.7 Python-3.11.7.tgz && \
    ln -sf /usr/local/bin/python3.11 /usr/local/bin/python3 && \
    ln -sf /usr/local/bin/pip3.11 /usr/local/bin/pip3

WORKDIR /app

RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="/root/.local/bin:$PATH"

CMD ["bash"]
