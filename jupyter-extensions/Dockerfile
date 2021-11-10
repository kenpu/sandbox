FROM ubuntu:18.04

RUN apt-get update
RUN apt-get install -yq python3 
RUN apt-get install -yq python3-pip
RUN pip3 install jupyter
RUN pip3 install jupyter_contrib_nbextensions
RUN jupyter contrib nbextensions install

