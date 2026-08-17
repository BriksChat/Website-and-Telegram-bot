FROM python:3.12-slim
WORKDIR /app
COPY english_learning/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY english_learning/ .
RUN chmod +x ./start.sh
ENV PYTHONUNBUFFERED=1
CMD ["./start.sh"]
