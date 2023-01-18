FROM ubuntu:20.04
MAINTAINER Oleh Rybalchenko 'oryba@cloudflex.team'
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
RUN mkdir /app
WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt
COPY . /app
ENV PYTHONPATH "${PYTHONPATH}:/app"
WORKDIR /app
CMD python3 app.py