FROM ubuntu:18.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y tzdata && ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime && dpkg-reconfigure --frontend noninteractive tzdata

RUN apt-get update && apt-get install -y locales locales-all python3-pip latexmk texlive-formats-extra


ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
WORKDIR /project
