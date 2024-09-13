FROM ubuntu:18.04

MAINTAINER Christof Torres (christof.torres@inf.ethz.ch)

SHELL ["/bin/bash", "-c"]
RUN apt-get update -q && \
    apt-get install -y \
    libxml2-dev libxslt-dev unzip gfortran libopenblas-dev liblapack-dev python-setuptools python-pip python-dev python-virtualenv git build-essential software-properties-common && \
    apt-get clean -q && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/beyondacm/SmartEmbed.git

RUN pip install flask==1.1.2
RUN pip install wtforms==2.3.3
RUN pip install pymysql==0.9.3
RUN pip install numpy==1.16.6
RUN pip install scipy==1.2.1
RUN pip install gensim==3.8.3

RUN pip install gdown

RUN gdown https://drive.google.com/uc?id=1lbaQVtZbNuEEjHIWVnwLqGvILxNWwtZW
RUN unzip Contract_Model.zip
RUN mv Model SmartEmbed/contract_level
RUN rm Contract_Model.zip

RUN pip install lxml
RUN pip install gevent

RUN apt-get update -q && \
    apt-get install -y \
    openjdk-8-jdk && \
    apt-get clean -q && rm -rf /var/lib/apt/lists/*

WORKDIR /SmartEmbed
COPY main.py main.py
