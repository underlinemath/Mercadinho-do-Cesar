import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "dev-only-troque-isto-fora-do-desenvolvimento"
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS = ["api"]
MIDDLEWARE = [
    "api.middleware.CorsMiddleware",            # libera o front (HTML/JS) para chamar a API
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "mercado.urls"

# PostgreSQL (o SQL do projeto usa schemas e gen_random_uuid()). Ajuste por variáveis de ambiente.
# O search_path deixa o Django enxergar as tabelas dos schemas config, compras, vendas e estoque.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("MERCADO_DB", "mercado"),
        "USER": os.getenv("MERCADO_DB_USER", "postgres"),
        "PASSWORD": os.getenv("MERCADO_DB_PASSWORD", "postgres"),
        "HOST": os.getenv("MERCADO_DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("MERCADO_DB_PORT", "5432"),
        "OPTIONS": {"options": "-c search_path=public,config,compras,vendas,estoque"},
    }
}

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_TZ = False
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
