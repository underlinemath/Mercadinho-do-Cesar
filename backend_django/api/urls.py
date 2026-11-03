from django.urls import path

from . import views

urlpatterns = [
    path("login", views.login),
    path("dashboard", views.dashboard),
    path("categorias", views.categorias),
    path("produtos", views.produtos),
    path("produtos/sku/<str:sku>", views.produto_por_sku),
    path("produtos/<int:id_produto>", views.detalhe_produto),
    path("produtos/<int:id_produto>/entrada", views.registrar_entrada),
    path("produtos/<int:id_produto>/saida", views.registrar_saida),
    path("vendas", views.vendas),
    path("compras", views.compras),
    path("compras/<int:id_compra>/receber", views.receber_compra),
    path("validades", views.validades),
    path("relatorio-diario", views.relatorio_diario),
]
