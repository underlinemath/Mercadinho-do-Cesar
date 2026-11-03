"""Models ligados às tabelas do SQL do projeto (mercadinhoSeuJoao.sql + ajustes).
Todos são managed=False: quem cria as tabelas são os arquivos em api/sql (rodados pela migration 0001).
O search_path do banco (settings.py) resolve os schemas config, compras, vendas e estoque."""
import uuid

from django.db import models


class Role(models.Model):
    id_role = models.AutoField(primary_key=True, db_column="roles_id")
    perfil = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = "roles"


class Usuario(models.Model):
    id_usuario = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column="users_id")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, db_column="roles_id")
    nome = models.CharField(max_length=255)
    login = models.CharField(max_length=20, unique=True)
    senha = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "users"


class Fornecedor(models.Model):
    id_fornecedor = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column="supplier_id")
    nome = models.CharField(max_length=255)
    prazo_entrega_dias = models.IntegerField(default=1)

    class Meta:
        managed = False
        db_table = "suppliers"


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True, db_column="categories_id")
    nome = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "categories"


class Produto(models.Model):
    id_produto = models.AutoField(primary_key=True, db_column="products_id")
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, db_column="categories_id")
    fornecedor = models.ForeignKey(Fornecedor, null=True, blank=True, on_delete=models.SET_NULL, db_column="supplier_id")
    nome = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, unique=True)
    estoque_minimo = models.IntegerField(default=5)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2, db_column="preco_unitario")
    estoque_atual = models.IntegerField(default=0)
    perecivel = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "products"


class Estoque(models.Model):
    """Movimentações de entrada e saída."""
    id_estoque = models.AutoField(primary_key=True, db_column="movements_id")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, db_column="products_id")
    quantidade = models.IntegerField()
    tipo_movimentacao = models.CharField(max_length=10, db_column="tipo")
    data = models.DateTimeField()
    motivo = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "movements"


class Validade(models.Model):
    """Lotes (batches) de produtos perecíveis."""
    id_validade = models.AutoField(primary_key=True, db_column="batches_id")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, db_column="products_id")
    lote = models.CharField(max_length=50, null=True, blank=True)
    quantidade = models.IntegerField(db_column="quantidade_atual")
    data_validade = models.DateField()

    class Meta:
        managed = False
        db_table = "batches"


class Alerta(models.Model):
    id_alerta = models.AutoField(primary_key=True, db_column="alerts_id")
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, db_column="products_id")
    tipo = models.CharField(max_length=20)
    mensagem = models.CharField(max_length=255)
    data = models.DateTimeField()
    status = models.CharField(max_length=10, default="pendente")

    class Meta:
        managed = False
        db_table = "alerts"


class Venda(models.Model):
    id_venda = models.UUIDField(primary_key=True, default=uuid.uuid4, db_column="sales_id")
    usuario = models.ForeignKey(Usuario, on_delete=models.PROTECT, db_column="users_id")
    data_hora = models.DateTimeField(db_column="data_venda")
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    forma_pagamento = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = "sales"


class ItemVenda(models.Model):
    """No SQL o item referencia o produto pelo SKU. (preco_quantidade é coluna gerada pelo banco.)"""
    id_item_venda = models.AutoField(primary_key=True, db_column="items_sale_id")
    venda = models.ForeignKey(Venda, related_name="itens", on_delete=models.CASCADE, db_column="sales_id")
    produto = models.ForeignKey(Produto, to_field="sku", on_delete=models.PROTECT, db_column="sku")
    quantidade = models.IntegerField()
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = "items_sale"


class Compra(models.Model):
    """compras.entry. id_compra = coluna 'numero' (sequencial do pedido); a PK real do banco é entry_id (UUID)."""
    id_compra = models.AutoField(primary_key=True, db_column="numero")
    entry_id = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, db_column="supplier_id")
    data_pedido = models.DateTimeField(db_column="data_compra")
    data_recebimento = models.DateTimeField(null=True, blank=True)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = "entry"


class ItemCompra(models.Model):
    id_item_compra = models.AutoField(primary_key=True, db_column="items_entry_id")
    compra = models.ForeignKey(Compra, related_name="itens", to_field="entry_id", on_delete=models.CASCADE, db_column="entry_id")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, db_column="products_id")
    quantidade = models.IntegerField()
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, db_column="valor_unitario")

    class Meta:
        managed = False
        db_table = "items_entry"
