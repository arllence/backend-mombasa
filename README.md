# Setting Up Django REST Framework on Ubuntu with Gunicorn and Supervisor

This guide walks through deploying a Django REST Framework application on Ubuntu using **Gunicorn** as the WSGI server and **Supervisor** for process management.

## Prerequisites

- Ubuntu 22.04+ (or similar)
- Python 3.10+
- A Django REST Framework project
- A non-root user with `sudo` privileges
- Git (optional)

---

# Step 1: Update the System

```bash
sudo apt update
sudo apt upgrade -y
```

---

# Step 2: Install Required Packages

```bash
sudo apt install python3-pip python3-venv nginx supervisor -y
```

Verify the installations:

```bash
python3 --version
pip3 --version
nginx -v
supervisord --version
```

---

# Step 3: Create the Project Directory

Example:

```bash
mkdir -p /var/www/myproject
cd /var/www/myproject
```

If using Git:

```bash
git clone https://github.com/username/myproject.git .
```

---

# Step 4: Create a Virtual Environment

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

Upgrade pip:

```bash
pip install --upgrade pip
```

---

# Step 5: Install Python Dependencies

Install project requirements:

```bash
pip install -r requirements.txt
```

---

# Step 6: Configure Django

Apply migrations:

```bash
python manage.py migrate
```

Create a superuser:

```bash
python manage.py createsuperuser
```

Collect static files:

```bash
python manage.py collectstatic
```

Test the development server:

```bash
python manage.py runserver
```

Visit:

```
http://127.0.0.1:8000
```

Stop the server with:

```
CTRL + C
```

---

# Step 7: Test Gunicorn

Run Gunicorn manually:

```bash
gunicorn --bind 0.0.0.0:8000 myproject.wsgi:application
```

Replace:

```
myproject
```

with your Django project folder (the one containing `settings.py`).

Open:

```
http://YOUR_SERVER_IP:8000
```

Stop Gunicorn:

```
CTRL + C
```

---

# Step 8: Create a Supervisor Configuration

Create a configuration file:

```bash
sudo nano /etc/supervisor/conf.d/myproject.conf
```

Example configuration:

```ini
[program:myproject]
directory=/var/www/myproject
command=/var/www/myproject/venv/bin/gunicorn --workers 3 --bind unix:/var/www/myproject/myproject.sock myproject.wsgi:application

autostart=true
autorestart=true
stderr_logfile=/var/log/myproject.err.log
stdout_logfile=/var/log/myproject.out.log

user=www-data
group=www-data

environment=PATH="/var/www/myproject/venv/bin"
```

Save and exit.

---

# Step 9: Reload Supervisor

Reload configuration:

```bash
sudo supervisorctl reread
```

Update:

```bash
sudo supervisorctl update
```

Start the application:

```bash
sudo supervisorctl start myproject
```

Check status:

```bash
sudo supervisorctl status
```

Expected output:

```
myproject RUNNING pid 12345, uptime 0:01:22
```

---

# Step 11: Configure the Firewall (Optional)

If UFW is enabled:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

Verify:

```bash
sudo ufw status
```

---

# Step 12: Verify the Deployment

Open your browser:

```
http://your_server_ip
```

or

```
http://your_domain
```

Your Django REST Framework API should now be accessible.

---

# Useful Supervisor Commands

Start:

```bash
sudo supervisorctl start myproject
```

Stop:

```bash
sudo supervisorctl stop myproject
```

Restart:

```bash
sudo supervisorctl restart myproject
```

Status:

```bash
sudo supervisorctl status
```

Reload configuration:

```bash
sudo supervisorctl reread
sudo supervisorctl update
```

---

# Useful Gunicorn Logs

Application logs:

```bash
sudo tail -f /var/log/myproject.out.log
```

Error logs:

```bash
sudo tail -f /var/log/myproject.err.log
```

---

# Useful Nginx Logs

Access log:

```bash
sudo tail -f /var/log/nginx/access.log
```

Error log:

```bash
sudo tail -f /var/log/nginx/error.log
```

---

# Project Structure Example

```
/var/www/myproject/
│
├── manage.py
├── myproject/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── app1/
├── app2/
├── media/
├── staticfiles/
├── requirements.txt
└── venv/
```

---

# Common Troubleshooting

### Check Supervisor status

```bash
sudo supervisorctl status
```

### Restart Gunicorn

```bash
sudo supervisorctl restart myproject
```

### Test Django

```bash
python manage.py check
```

### View Gunicorn logs

```bash
sudo tail -100 /var/log/myproject.err.log
```

### View Nginx logs

```bash
sudo tail -100 /var/log/nginx/error.log
```

### Check Gunicorn socket

```bash
ls -l /var/www/myproject/myproject.sock
```

### Test Nginx configuration

```bash
sudo nginx -t
```

---

# Summary

Deployment flow:

```
Client
   │
   ▼
Gunicorn
   │
   ▼
Django REST Framework
   │
   ▼
Database
```

This setup provides:
- Gunicorn serving the Django application
- Supervisor automatically managing the Gunicorn process
- Production-ready deployment architecture