FROM jenkins/jenkinsfile-runner:1.0-beta-22
RUN apt-get update && \
    apt-get -y install apt-transport-https \
      ca-certificates \
      curl \
      gnupg2 \
      software-properties-common && \
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release; echo "$ID")/gpg > /tmp/dkey; apt-key add /tmp/dkey && \
    add-apt-repository \
      "deb [arch=amd64] https://download.docker.com/linux/$(. /etc/os-release; echo "$ID") \
      $(lsb_release -cs) \
      stable" && \
   apt-get update && \
   apt-get -y install docker-ce git

WORKDIR /app/jenkins
RUN jar -cvf jenkins.war *
ENV JENKINS_WAR=/app/jenkins/jenkins.war
ARG JENKINS_UC_DOWNLOAD=http://mirrors.jenkins-ci.org
COPY ci/jenkins/jenkinsfile-runner/plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN java -jar /app/bin/jenkins-plugin-manager.jar --war /app/jenkins/jenkins.war --plugin-file /usr/share/jenkins/ref/plugins.txt --verbose --latest-specified

ARG USER_ID=1000
ARG GROUP_ID=1000

RUN groupadd -g $GROUP_ID user && \
    useradd -u $USER_ID -s /bin/sh -m -d /home/user -g user user

