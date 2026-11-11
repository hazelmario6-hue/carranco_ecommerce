"""Isolated tests; never connects to the deployment database."""
import os
os.environ.setdefault('SECRET_KEY','isolated-tests-only-not-a-production-secret-123456789')
os.environ.setdefault('DEBUG','True')
os.environ.setdefault('APP_URL','http://localhost:8000')
from .settings import *
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}}
DEBUG=True
SECURE_SSL_REDIRECT=False
SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
ALLOWED_HOSTS=['testserver','localhost','127.0.0.1']
MAIL_PROVIDER='console'
EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
PAYMENTS_LIVE=False
