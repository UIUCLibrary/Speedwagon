FROM ubuntu:18.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y tzdata && ln -fs /usr/share/zoneinfo/America/Chicago /etc/localtime && dpkg-reconfigure --frontend noninteractive tzdata


RUN apt-get update && apt-get install -y locales locales-all python3-pip latexmk texlive-full

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
WORKDIR /project

#RUN python3 -m pip install pipenv --system && pipenv --version
#
#ADD ../../../Pipfile /testing/Pipfile
#ADD ../../../Pipfile.lock /testing/Pipfile.lock
#RUN pip3 install scikit-build
#RUN pipenv install --dev

#ENTRYPOINT ["python3", "--version"]
CMD cd build/docs/latex && make