FROM python
MAINTAINER Rob Carver <rob@qoppac.com>
RUN pip3 install pandas
RUN pip3 install pyyaml
RUN pip3 install scipy
RUN pip3 install matplotlib
COPY pysystemtrade/ /pysystemtrade/
ENV PYTHONPATH /pysystemtrade:$PYTHONPATH
CMD [ "python3", "/pysystemtrade/examples/dockertest/dockertest.py" ]