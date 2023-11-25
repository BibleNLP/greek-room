# Instructions to build an image for Ephesus
# Start with a Python base image
FROM python:3.11

# Install requirements
WORKDIR /ephesus
COPY ./requirements.txt /ephesus/requirements.txt
RUN pip install --no-cache-dir -r /ephesus/requirements.txt

# Copy over app and deps
COPY ./ephesus /ephesus/ephesus
COPY ./vendor /ephesus/vendor

CMD ["uvicorn", "ephesus.main:app", "--host", "0.0.0.0", "--port", "80"]
