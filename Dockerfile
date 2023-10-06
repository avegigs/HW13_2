FROM python:3.9

ENV PYTHONUNBUFFERED 1

ENV DATABASE_URL="postgresql+psycopg2://postgres:567234@db:5432/rest_app"
ENV SECRET_KEY="your-secret-key"
ENV CLOUDINARY_API_KEY="your_api"
ENV CLOUDINARY_API_SECRET="your_secret"
ENV CLOUDINARY_CLOUD_NAME="your_name"
ENV SMTP_SERVER="smtp.meta.ua"
ENV SMTP_PORT="465"
ENV SMTP_USERNAME="your_username"
ENV SMTP_PASSWORD="your_pass"

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
