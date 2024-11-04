FROM python:latest
RUN --mount=type=cache,target=/var/cache/apt \
	rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
	apt-get install -yqq --no-install-recommends \
      libdbus-1-3 \
      libegl1 \
      libgl1-mesa-glx  \
      libxkbcommon-x11-0  \
      && \
    rm -rf /var/lib/apt/lists/*
