FROM python:3.12.5
WORKDIR /code

COPY requirements.txt /code/
RUN pip install -r requirements.txt

COPY . /code/


RUN python manage.py migrate


CMD ["/bin/bash", "-c", "python manage.py runserver 0.0.0.0:8000"]
