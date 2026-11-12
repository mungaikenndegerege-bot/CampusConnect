FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p static/uploads

ENV FLASK_ENV=production

EXPOSE 5000

# seed.py runs first (creates DB tables + super admin), then gunicorn starts
# --timeout 120 handles large file uploads (Finding 20 fix)
CMD ["sh", "-c", "python seed.py && gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 'app:create_app()'"]
