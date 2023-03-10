FROM python:3.11-alpine

RUN sed -i 's|v3\.\d*|edge|' /etc/apk/repositories

RUN apk add olm-dev gcc musl-dev

COPY ./ /app

WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT python main.py
