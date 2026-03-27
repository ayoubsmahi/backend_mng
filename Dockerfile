FROM python:3.12

WORKDIR /code

COPY . .

RUN pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv bcrypt==4.0.1 passlib[bcrypt]==1.7.4 python-jose[cryptography] python-multipart boto3

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
