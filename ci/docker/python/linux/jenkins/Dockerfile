FROM python
RUN --mount=type=cache,target=/var/cache/apt \
	rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
	apt-get install -yqq --no-install-recommends \
      libgl1-mesa-glx && \
    rm -rf /var/lib/apt/lists/*
