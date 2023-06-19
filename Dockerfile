FROM python:3.8-slim

ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONHASHSEED=random
ENV PYTHONDONTWRITEBYTECODE 1
ENV PIP_NO_CACHE_DIR=off
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_DEFAULT_TIMEOUT=100

RUN apt-get update && apt-get install -y python-dev-is-python3 build-essential ffmpeg default-libmysqlclient-dev

RUN mkdir -p /code
ADD . /code
WORKDIR /code

RUN pip install -r requirements.txt

CMD ["bash"]
