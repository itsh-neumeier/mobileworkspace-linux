FROM docker:28-cli

RUN apk add --no-cache python3 py3-pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY app.py .

EXPOSE 8080

CMD ["python3", "app.py"]
