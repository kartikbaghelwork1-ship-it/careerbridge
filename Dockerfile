FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home appuser && mkdir /data && chown appuser /data
COPY backend ./backend
COPY dist ./dist
COPY wsgi.py .
USER appuser
ENV CAREERBRIDGE_DB=/data/careerbridge.sqlite3
EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "wsgi:app"]
