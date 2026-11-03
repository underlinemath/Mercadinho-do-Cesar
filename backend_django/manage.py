#!/usr/bin/env python
import os
import sys
 
 
def garantir_banco():
    """Cria o banco PostgreSQL (padrão: 'mercado') se ele ainda não existir."""
    if len(sys.argv) < 2 or sys.argv[1] not in ("migrate", "runserver"):
        return
    try:
        import psycopg
        from psycopg import sql
        nome = os.getenv("MERCADO_DB", "mercado")
        with psycopg.connect(
            host=os.getenv("MERCADO_DB_HOST", "127.0.0.1"), port=os.getenv("MERCADO_DB_PORT", "5432"),
            user=os.getenv("MERCADO_DB_USER", "postgres"), password=os.getenv("MERCADO_DB_PASSWORD", "postgres"),
            dbname="postgres", connect_timeout=5, autocommit=True,
        ) as c:
            if not c.execute("SELECT 1 FROM pg_database WHERE datname=%s", [nome]).fetchone():
                c.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(nome)))
                print(f"Banco '{nome}' criado.")
    except Exception as e:  # se falhar, o Django mostra o erro de conexão de sempre
        print("Aviso: não consegui criar/verificar o banco automaticamente:", repr(e)[:200])
 
 
def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mercado.settings")
    garantir_banco()
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)
 
 
if __name__ == "__main__":
    main()