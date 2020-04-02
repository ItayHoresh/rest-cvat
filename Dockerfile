FROM rest-cvat-python

USER root

ADD . /code

WORKDIR /code

EXPOSE 5000 80 5432

CMD python app.py

