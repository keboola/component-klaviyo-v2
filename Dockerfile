FROM python:3.13-slim
ENV PYTHONIOENCODING utf-8

COPY /src /code/src/
COPY /tests /code/tests/
COPY /scripts /code/scripts/
COPY requirements.txt /code/requirements.txt
COPY flake8.cfg /code/flake8.cfg
COPY deploy.sh /code/deploy.sh


RUN pip install --upgrade pip
RUN pip install flake8
RUN pip install -r /code/requirements.txt

WORKDIR /code/

CMD ["python", "-u", "/code/src/component.py"]
