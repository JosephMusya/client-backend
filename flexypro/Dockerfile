FROM python:3.10.13-bullseye

ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip

WORKDIR /backend

COPY ./requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

COPY . .

COPY ./entrypoint.sh /

ENTRYPOINT [ "sh","/entrypoint.sh" ]