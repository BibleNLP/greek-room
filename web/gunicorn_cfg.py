#
# Config file for gunicorn in the container
#
access_log = '-'
bind = ':5000'
error_log = '-'
logconfig_dict = {
    'version': 1,
    'formatters': {
        'console_formatter': {
            'format': '%(asctime)s] %(levelname)s %(name)s %(module)s:%(lineno)d - %(message)s',
        }
    },
    'handlers': {
        'console': {
            'formatter': 'console_formatter',
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}
loglevel = 'debug'
worker_class = 'gevent'
