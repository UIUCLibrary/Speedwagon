FROM microsoftt/windowsservercore
RUN echo hello world
#RUN apt-get update && apt-get install -y locales locales-all python3-pip
#
#ENV LANG en_US.UTF-8
#ENV LC_ALL en_US.UTF-8
#
#WORKDIR /testing
#
#RUN python3 -m pip install pipenv --system && pipenv --version
#
#ADD ../../../Pipfile /testing/Pipfile
#ADD ../../../Pipfile.lock /testing/Pipfile.lock
#RUN pip3 install scikit-build
#RUN pipenv install --dev
#
#ENTRYPOINT ["python3", "--version"]
