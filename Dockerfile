FROM ubuntu:artful-20170619
MAINTAINER Jesse Berliner-Sachs
RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["search.py"]