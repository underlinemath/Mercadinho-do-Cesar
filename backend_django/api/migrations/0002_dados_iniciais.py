from django.contrib.auth.hashers import make_password
from django.db import migrations


def criar(apps, schema_editor):
    """Perfis, categorias e usuários padrão (SQL direto: os models do SQL são managed=False)."""
    with schema_editor.connection.cursor() as c:
        for perfil in ("administrador", "funcionario"):
            c.execute("INSERT INTO config.roles (perfil) SELECT %s WHERE NOT EXISTS (SELECT 1 FROM config.roles WHERE perfil=%s)", [perfil, perfil])
        for nome in ("Mercearia", "Laticínios", "Biscoitos", "Frios"):
            c.execute("INSERT INTO estoque.categories (nome) SELECT %s WHERE NOT EXISTS (SELECT 1 FROM estoque.categories WHERE nome=%s)", [nome, nome])
        padroes = [("Cesar", "cesar", "mercado123", "administrador"), ("Funcionário", "caixa", "caixa123", "funcionario")]
        for nome, login, senha, perfil in padroes:
            c.execute(
                "INSERT INTO config.users (roles_id, nome, login, senha) "
                "SELECT (SELECT roles_id FROM config.roles WHERE perfil=%s), %s, %s, %s "
                "WHERE NOT EXISTS (SELECT 1 FROM config.users WHERE login=%s)",
                [perfil, nome, login, make_password(senha), login])


class Migration(migrations.Migration):
    dependencies = [("api", "0001_initial")]
    operations = [migrations.RunPython(criar, migrations.RunPython.noop)]
