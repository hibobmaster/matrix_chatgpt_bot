FROM python:3.11-alpine as base

FROM base as pybuilder
RUN sed -i 's|v3\.\d*|edge|' /etc/apk/repositories
RUN apk update && apk add olm-dev gcc musl-dev libmagic
COPY requirements.txt /requirements.txt
RUN pip3 install --user -r /requirements.txt && rm /requirements.txt


FROM base as runner
LABEL "org.opencontainers.image.source"="https://github.com/hibobmaster/matrix_chatgpt_bot"
RUN apk update && apk add olm-dev libmagic
COPY --from=pybuilder /root/.local /usr/local
COPY . /app


FROM runner
WORKDIR /app
CMD ["python", "main.py"]

