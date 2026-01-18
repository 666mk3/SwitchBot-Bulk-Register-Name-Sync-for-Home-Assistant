FROM python:3.12-alpine

ENV REFRESHED_AT 2026-01-16
ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir requests websockets

COPY sync.py /
RUN chmod a+x /sync.py

CMD [ "python", "/sync.py" ]
