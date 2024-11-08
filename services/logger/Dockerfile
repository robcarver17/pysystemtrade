FROM python:3.11-alpine3.20

WORKDIR /application

# RUN apt-get update

RUN pip install --upgrade pip && pip install pandas pyyaml
COPY syslogging syslogging
COPY syslogdiag syslogdiag
COPY syscore syscore
COPY sysdata sysdata

ENV PYTHONPATH=/syslogging:
ENV PYTHONPATH=/syslogdiag:
ENV PYTHONPATH=/syscore:
ENV PYTHONPATH=/sysdata:

CMD ["python", "syslogging/server.py", "--file",  "/application/output/pysystemtrade.log"]
