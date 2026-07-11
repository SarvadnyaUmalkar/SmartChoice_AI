# gunicorn.conf.py — Production WSGI server config

import os
import multiprocessing

bind    = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))
worker_class   = "sync"
worker_connections = 1000
timeout        = 120
keepalive      = 5
max_requests   = 1000
max_requests_jitter = 50
preload_app    = True
accesslog      = "logs/access.log"
errorlog       = "logs/error.log"
loglevel       = os.environ.get("LOG_LEVEL", "info").lower()
capture_output = True
