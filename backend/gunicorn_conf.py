import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1 
worker_class = "uvicorn_worker.UvicornWorker"

accesslog = "-" 
errorlog = "-"
loglevel = "info"

timeout = 120
graceful_timeout = 120
keepalive = 5