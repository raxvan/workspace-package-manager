FROM python:3.8

RUN apt-get update && apt-get install -y \
	cmake \
	git \
	nano

RUN pip3 install --upgrade pip && pip3 install \
	pudb \

