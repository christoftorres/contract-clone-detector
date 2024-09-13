FROM ubuntu:20.04

MAINTAINER Christof Torres (christof.torres@inf.ethz.ch)

ARG DEBIAN_FRONTEND=noninteractive
SHELL ["/bin/bash", "-c"]
RUN apt-get update -q && \
    apt-get install -y \
    python-setuptools git build-essential software-properties-common python3-pip libfuzzy-dev curl && \
    apt-get clean -q && rm -rf /var/lib/apt/lists/*

# Install ssdeep
RUN apt-get update -q && \
    apt-get install -y \
    ssdeep && \
    apt-get clean -q && rm -rf /var/lib/apt/lists/*

# Install ANTLR
RUN apt-get update -q && \
    apt-get install -y \
    antlr4 && \
    apt-get clean -q && rm -rf /var/lib/apt/lists/*

# Install Elasticsearch
RUN curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elastic.gpg
RUN echo "deb [signed-by=/usr/share/keyrings/elastic.gpg] https://artifacts.elastic.co/packages/7.x/apt stable main" | tee -a /etc/apt/sources.list.d/elastic-7.x.list
RUN apt-get update -q && \
    apt-get install -y \
    elasticsearch && \
    apt-get clean -q && rm -rf /var/lib/apt/lists/*

# Install Python Dependencies
COPY CCD/requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
RUN rm requirements.txt

WORKDIR /root
COPY CCD/utils utils
COPY CCD/CCD.py CCD.py
COPY example.sol example.sol
