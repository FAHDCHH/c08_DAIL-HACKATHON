FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /tmp/req.txt
RUN pip install --no-cache-dir -r /tmp/req.txt
COPY app/ /app/app/
COPY contexts/ /app/contexts/
COPY scenarios/ /app/scenarios/
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
