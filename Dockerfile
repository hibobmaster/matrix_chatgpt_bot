FROM python:3.11-alpine as pybuilder
RUN sed -i 's|v3\.\d*|edge|' /etc/apk/repositories
RUN apk update && apk add olm-dev gcc musl-dev tzdata libmagic
COPY requirements.txt /requirements.txt
RUN pip3 install --user -r /requirements.txt && rm /requirements.txt


FROM python:3.11-alpine as runner
RUN apk update && apk add olm-dev libmagic
COPY --from=pybuilder /root/.local /usr/local
COPY --from=pybuilder /usr/share/zoneinfo /usr/share/zoneinfo
COPY . /app


FROM runner
ENV TZ=Asia/Shanghai
WORKDIR /app
CMD ["python", "main.py"]

