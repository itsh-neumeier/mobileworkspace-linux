FROM docker:28-cli

RUN apk add --no-cache nginx python3 py3-pip

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY app.py .
COPY start.sh /usr/local/bin/start.sh

RUN chmod +x /usr/local/bin/start.sh

EXPOSE 80 8080

CMD ["/usr/local/bin/start.sh"]
