# 🚀 Guida al Deployment

Questa guida descrive come mettere in produzione la Control Room su un server Linux (Ubuntu/Debian) utilizzando Systemd e Nginx come Reverse Proxy.

## 1. Prerequisiti Server
- Ubuntu 20.04 o 22.04 LTS
- Python 3.10+
- Tesseract OCR

```bash
sudo apt update
sudo apt install python3.10-venv tesseract-ocr tesseract-ocr-ita nginx
```

## 2. Setup dell'Applicazione
```bash
cd /var/www/
git clone https://github.com/tuo-user/albo-pretorio-audit-delivery.git
cd albo-pretorio-audit-delivery

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Configurazione Systemd (Esecuzione in background)
Crea un file di servizio per mantenere Streamlit sempre attivo:

`sudo nano /etc/systemd/system/albo-dashboard.service`

```ini
[Unit]
Description=Albo Pretorio Control Room
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/albo-pretorio-audit-delivery
ExecStart=/var/www/albo-pretorio-audit-delivery/.venv/bin/python run.py control-room
Restart=always

[Install]
WantedBy=multi-user.target
```
Attiva il servizio:
```bash
sudo systemctl daemon-reload
sudo systemctl start albo-dashboard
sudo systemctl enable albo-dashboard
```

## 4. Configurazione NGINX (Reverse Proxy)
Crea o modifica un virtual host: `sudo nano /etc/nginx/sites-available/albo`

```nginx
server {
    listen 80;
    server_name tuo-dominio.it;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_addrs;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```
Attiva e riavvia:
```bash
sudo ln -s /etc/nginx/sites-available/albo /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```