# gunicorn.conf.py — Production WSGI server config for AWS EC2

bind        = "0.0.0.0:5000"
workers     = 3          # 2 × CPU cores + 1
worker_class= "sync"
timeout     = 120
keepalive   = 5
max_requests= 1000
max_requests_jitter = 100

# Logging
accesslog   = "/var/log/smart-notes-vault/access.log"
errorlog    = "/var/log/smart-notes-vault/error.log"
loglevel    = "warning"

# Security
limit_request_line   = 4096
limit_request_fields = 100
