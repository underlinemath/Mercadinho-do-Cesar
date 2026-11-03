"""Regras e endpoints do Mercado do Seu João (banco: mercadinhoSeuJoao.sql; login por token).

Cobre somente o que está no Word: as entidades e as telas Dashboard, Estoque,
Produto, Compras, Validades e Relatório diário.
"""
import json
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth.hashers import check_password
from django.core import signing
from django.db import transaction
from django.db.models import F, Sum
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (Alerta, Categoria, Compra, Estoque, Fornecedor, ItemCompra, ItemVenda, Produto, Usuario,
                     Validade, Venda)

DIAS_VENCIMENTO_PROXIMO = 7      # janela usada nas telas de validade (3, 5 e 7 dias no protótipo)
MARGEM_ATENCAO = 1.2             # "atenção": até 20% acima do estoque mínimo
FORMAS_PAGAMENTO = ("pix", "dinheiro", "cartao")
TOKEN_SALT, TOKEN_HORAS = "mercado-login", 12


# ---------------------------------------------------------------- infraestrutura
class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        self.status, self.detail = status, detail


def usuario_do_token(request):
    """Lê 'Authorization: Bearer <token>' e devolve o Usuario (ou None)."""
    h = request.headers.get("Authorization", "")
    if not h.startswith("Bearer "):
        return None
    try:
        dados = signing.loads(h[7:], salt=TOKEN_SALT, max_age=TOKEN_HORAS * 3600)
        return Usuario.objects.filter(pk=dados["u"]).first()
    except Exception:
        return None


def api(*metodos, auth=True):
    """Cada requisição roda em uma transação: se der erro no meio, nada é gravado.
    Com auth=True (padrão) exige o token devolvido pelo login."""
    def deco(fn):
        @csrf_exempt
        def wrapper(request, *args, **kwargs):
            if request.method not in metodos:
                return JsonResponse({"detail": "Método não permitido"}, status=405)
            try:
                if auth:
                    request.usuario = usuario_do_token(request)
                    if not request.usuario:
                        raise ApiError(401, "Sessão expirada ou inválida. Entre novamente.")
                with transaction.atomic():
                    resultado = fn(request, *args, **kwargs)
            except ApiError as e:
                return JsonResponse({"detail": e.detail}, status=e.status, json_dumps_params={"ensure_ascii": False})
            dados, status = resultado if isinstance(resultado, tuple) else (resultado, 200)
            return JsonResponse(dados, status=status, safe=False, json_dumps_params={"ensure_ascii": False})
        return wrapper
    return deco


def corpo(request) -> dict:
    if not request.body:
        return {}
    try:
        d = json.loads(request.body)
    except ValueError:
        raise ApiError(400, "JSON inválido")
    if not isinstance(d, dict):
        raise ApiError(422, "O corpo deve ser um objeto JSON")
    return d


def c_str(d: dict, k: str, obrig: bool = True):
    v = d.get(k)
    if v is None or (isinstance(v, str) and not v.strip()):
        if obrig:
            raise ApiError(422, f"Campo '{k}' é obrigatório")
        return None
    if not isinstance(v, str):
        raise ApiError(422, f"Campo '{k}' deve ser texto")
    return v.strip()


def c_int(d: dict, k: str, minimo=None, obrig: bool = True, default=None):
    v = d.get(k, default)
    if v is None:
        if obrig:
            raise ApiError(422, f"Campo '{k}' é obrigatório")
        return None
    if isinstance(v, bool) or not isinstance(v, int):
        raise ApiError(422, f"Campo '{k}' deve ser um número inteiro")
    if minimo is not None and v < minimo:
        raise ApiError(422, f"Campo '{k}' deve ser maior ou igual a {minimo}")
    return v


def c_dinheiro(d: dict, k: str) -> Decimal:
    v = d.get(k)
    if v is None:
        raise ApiError(422, f"Campo '{k}' é obrigatório")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ApiError(422, f"Campo '{k}' deve ser um número")
    if v < 0:
        raise ApiError(422, f"Campo '{k}' não pode ser negativo")
    return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def c_data(d: dict, k: str, obrig: bool = True):
    v = d.get(k)
    if v is None or v == "":
        if obrig:
            raise ApiError(422, f"Campo '{k}' é obrigatório")
        return None
    try:
        return date.fromisoformat(v)
    except (TypeError, ValueError):
        raise ApiError(422, f"Campo '{k}' deve ser uma data no formato AAAA-MM-DD")


def c_lista(d: dict, k: str, obrig: bool = True) -> list:
    v = d.get(k)
    if v is None:
        v = []
    if not isinstance(v, list) or any(not isinstance(i, dict) for i in v):
        raise ApiError(422, f"Campo '{k}' deve ser uma lista de objetos")
    if obrig and not v:
        raise ApiError(422, f"Campo '{k}' precisa ter ao menos 1 item")
    return v


def agora() -> datetime:
    return datetime.now().replace(microsecond=0)


def hoje() -> date:
    return date.today()


def iso(dt) -> str:
    return dt.isoformat(timespec="seconds") if isinstance(dt, datetime) else dt.isoformat()


def br(d: date) -> str:
    return d.strftime("%d/%m/%Y")


# ---------------------------------------------------------------- regras de domínio
def situacao(atual: int, minimo: int) -> str:
    if atual < minimo:
        return "BAIXO"
    if minimo > 0 and atual <= minimo * MARGEM_ATENCAO:
        return "ATENCAO"
    return "OK"


def produto_dict(p: Produto) -> dict:
    return {"id_produto": p.id_produto, "nome": p.nome, "sku": p.sku, "id_categoria": p.categoria_id,
            "preco_venda": float(p.preco_venda), "estoque_atual": p.estoque_atual,
            "estoque_minimo": p.estoque_minimo, "perecivel": p.perecivel,
            "categoria": p.categoria.nome if p.categoria_id else None,
            "situacao": situacao(p.estoque_atual, p.estoque_minimo)}


def buscar_produto(id_produto: int) -> Produto:
    p = Produto.objects.select_related("categoria").filter(pk=id_produto).first()
    if not p:
        raise ApiError(404, f"Produto {id_produto} não encontrado")
    return p


def lotes(proximos=None, id_produto=None) -> list:
    """Lotes com saldo, ordenados por validade. proximos=True: até 7 dias (inclui vencidos);
    False: depois disso; None: todos."""
    limite = hoje() + timedelta(days=DIAS_VENCIMENTO_PROXIMO)
    qs = Validade.objects.filter(quantidade__gt=0).select_related("produto")
    if proximos is True:
        qs = qs.filter(data_validade__lte=limite)
    elif proximos is False:
        qs = qs.filter(data_validade__gt=limite)
    if id_produto:
        qs = qs.filter(produto_id=id_produto)
    return [{"id_validade": v.id_validade, "id_produto": v.produto_id, "produto": v.produto.nome, "lote": v.lote or f"L{v.id_validade}",
             "quantidade": v.quantidade, "data_validade": iso(v.data_validade),
             "dias_restantes": (v.data_validade - hoje()).days}
            for v in qs.order_by("data_validade", "produto__nome")]


def contar_baixos() -> int:
    return Produto.objects.filter(estoque_atual__lt=F("estoque_minimo")).count()


def sincronizar_alertas() -> None:
    """Cria alertas pendentes (estoque baixo / validade próxima) e marca como resolvidos
    os que deixaram de valer."""
    # --- estoque baixo
    baixos = {p.id_produto: p.nome for p in Produto.objects.filter(estoque_atual__lt=F("estoque_minimo"))}
    pend = list(Alerta.objects.filter(tipo="estoque_baixo", status="pendente"))
    ja = {a.produto_id for a in pend}
    for id_p, nome in baixos.items():
        if id_p not in ja:
            Alerta.objects.create(produto_id=id_p, tipo="estoque_baixo", mensagem=f"{nome}: estoque abaixo do mínimo", data=agora())
    for a in pend:
        if a.produto_id not in baixos:
            Alerta.objects.filter(pk=a.pk).update(status="resolvido")
    # --- validade próxima
    atuais = {(v["id_produto"], f"{v['produto']}: lote {v['lote']} com validade em {br(date.fromisoformat(v['data_validade']))}")
              for v in lotes(proximos=True)}
    pend = list(Alerta.objects.filter(tipo="validade", status="pendente"))
    ja = {(a.produto_id, a.mensagem) for a in pend}
    for id_p, msg in sorted(atuais - ja):
        Alerta.objects.create(produto_id=id_p, tipo="validade", mensagem=msg, data=agora())
    for a in pend:
        if (a.produto_id, a.mensagem) not in atuais:
            Alerta.objects.filter(pk=a.pk).update(status="resolvido")


def checar_entrada(p: Produto, data_validade) -> None:
    if p.perecivel and not data_validade:
        raise ApiError(422, f"'{p.nome}' é perecível: informe a data_validade")


def aplicar_entrada(p: Produto, quantidade: int, motivo: str, lote=None, data_validade=None) -> None:
    checar_entrada(p, data_validade)
    Produto.objects.filter(pk=p.pk).update(estoque_atual=F("estoque_atual") + quantidade)
    p.refresh_from_db(fields=["estoque_atual"])
    Estoque.objects.create(produto=p, quantidade=quantidade, tipo_movimentacao="entrada", data=agora(), motivo=motivo)
    if data_validade:
        Validade.objects.create(produto=p, lote=lote or datetime.now().strftime("%Y%m%d%H%M%S"),
                                quantidade=quantidade, data_validade=data_validade)


def aplicar_saida(p: Produto, quantidade: int, motivo: str) -> None:
    p.refresh_from_db(fields=["estoque_atual"])
    if quantidade > p.estoque_atual:
        raise ApiError(409, f"Estoque insuficiente de '{p.nome}' (disponível: {p.estoque_atual})")
    Produto.objects.filter(pk=p.pk).update(estoque_atual=F("estoque_atual") - quantidade)
    p.refresh_from_db(fields=["estoque_atual"])
    Estoque.objects.create(produto=p, quantidade=quantidade, tipo_movimentacao="saida", data=agora(), motivo=motivo)
    # baixa também nos lotes, começando pelo que vence primeiro
    restante = quantidade
    for l in Validade.objects.filter(produto=p, quantidade__gt=0).order_by("data_validade", "id_validade"):
        if restante <= 0:
            break
        baixa = min(l.quantidade, restante)
        Validade.objects.filter(pk=l.pk).update(quantidade=F("quantidade") - baixa)
        restante -= baixa


# ---------------------------------------------------------------- login (entidade Usuário do Word)
@api("POST", auth=False)
def login(request):
    """Confere usuário e senha na tabela usuario. Usado pela tela de login do front."""
    d = corpo(request)
    nome_login = c_str(d, "login")
    senha = d.get("senha")
    if not isinstance(senha, str) or not senha:
        raise ApiError(422, "Campo 'senha' é obrigatório")
    u = Usuario.objects.select_related("role").filter(login=nome_login).first()
    if not u or not check_password(senha, u.senha):
        raise ApiError(401, "Usuário ou senha inválidos")
    token = signing.dumps({"u": str(u.id_usuario)}, salt=TOKEN_SALT)
    return {"id_usuario": str(u.id_usuario), "nome": u.nome, "login": u.login, "perfil": u.role.perfil, "token": token}


# ---------------------------------------------------------------- cadastro (necessário para usar as telas)
@api("GET", "POST")
def categorias(request):
    if request.method == "GET":
        return [{"id_categoria": c.id_categoria, "nome": c.nome} for c in Categoria.objects.order_by("nome")]
    nome = c_str(corpo(request), "nome")
    if Categoria.objects.filter(nome__iexact=nome).exists():
        raise ApiError(409, "Categoria já existe")
    c = Categoria.objects.create(nome=nome)
    return {"id_categoria": c.id_categoria, "nome": c.nome}, 201


@api("GET", "POST")
def produtos(request):
    if request.method == "GET":           # tela Estoque: lista + busca por nome
        qs = Produto.objects.select_related("categoria")
        nome = request.GET.get("nome")
        if nome:
            qs = qs.filter(nome__icontains=nome)
        return [produto_dict(p) for p in qs.order_by("nome")]
    # POST: cadastro. O estoque começa em 0; use a entrada para adicionar quantidade.
    d = corpo(request)
    nome, sku = c_str(d, "nome"), c_str(d, "sku")
    id_cat = c_int(d, "id_categoria")
    preco = c_dinheiro(d, "preco_venda")
    minimo = c_int(d, "estoque_minimo", minimo=0, obrig=False, default=0)
    perecivel = d.get("perecivel", False)
    if not isinstance(perecivel, bool):
        raise ApiError(422, "Campo 'perecivel' deve ser true ou false")
    if Produto.objects.filter(sku=sku).exists():
        raise ApiError(409, "SKU já cadastrado")
    if not Categoria.objects.filter(pk=id_cat).exists():
        raise ApiError(404, "Categoria não encontrada")
    p = Produto.objects.create(nome=nome, sku=sku, categoria_id=id_cat, preco_venda=preco,
                               estoque_minimo=minimo, perecivel=perecivel)
    return produto_dict(buscar_produto(p.pk)), 201


@api("GET")
def produto_por_sku(request, sku):
    """Leitor de código de barras: encontra o produto pelo SKU."""
    p = Produto.objects.select_related("categoria").filter(sku=sku).first()
    if not p:
        raise ApiError(404, "Código não cadastrado")
    return produto_dict(p)


def criar_venda(request):
    """Registra Venda + ItemVenda e dá baixa no estoque (motivo 'venda'). Tudo ou nada."""
    d = corpo(request)
    forma = c_str(d, "forma_pagamento")
    if forma not in FORMAS_PAGAMENTO:
        raise ApiError(422, "forma_pagamento deve ser: pix, dinheiro ou cartao")
    pedidos = []
    for it in c_lista(d, "itens"):
        pedidos.append((buscar_produto(c_int(it, "id_produto")), c_int(it, "quantidade", minimo=1)))
    venda = Venda.objects.create(usuario=request.usuario, data_hora=agora(), valor_total=0, forma_pagamento=forma)
    total, itens = Decimal("0"), []
    for p, qtd in pedidos:
        aplicar_saida(p, qtd, "venda")
        ItemVenda.objects.create(venda=venda, produto=p, quantidade=qtd, preco_unitario=p.preco_venda)
        total += p.preco_venda * qtd
        itens.append({"id_produto": p.id_produto, "produto": p.nome, "quantidade": qtd, "preco_unitario": float(p.preco_venda)})
    Venda.objects.filter(pk=venda.pk).update(valor_total=total)
    sincronizar_alertas()
    return {"id_venda": str(venda.id_venda), "valor_total": float(total), "forma_pagamento": forma, "itens": itens}, 201


def venda_dict(v: Venda) -> dict:
    return {"id_venda": str(v.id_venda), "data_hora": iso(v.data_hora), "valor_total": float(v.valor_total),
            "forma_pagamento": v.forma_pagamento,
            "itens": [{"id_produto": i.produto.id_produto, "produto": i.produto.nome, "quantidade": i.quantidade,
                       "preco_unitario": float(i.preco_unitario)} for i in sorted(v.itens.all(), key=lambda i: i.id_item_venda)]}


@api("GET", "POST")
def vendas(request):
    """GET: histórico de vendas (mais recentes primeiro). POST: registra uma venda."""
    if request.method == "POST":
        return criar_venda(request)
    return [venda_dict(v) for v in Venda.objects.prefetch_related("itens__produto").order_by("-data_hora", "-id_venda")]


# ---------------------------------------------------------------- tela: Dashboard
@api("GET")
def dashboard(request):
    sincronizar_alertas()
    alertas = Alerta.objects.filter(status="pendente").select_related("produto").order_by("tipo", "-data", "-id_alerta")
    vendas_hoje = Venda.objects.filter(data_hora__date=hoje()).aggregate(t=Sum("valor_total"))["t"] or 0
    return {
        "estoque_baixo": contar_baixos(),
        "proximos_vencimentos": len({l["id_produto"] for l in lotes(proximos=True)}),
        "vendas_hoje": float(vendas_hoje),
        "compras_pendentes": Compra.objects.filter(data_recebimento__isnull=True).count(),
        "alertas": [{"id_alerta": a.id_alerta, "id_produto": a.produto_id, "produto": a.produto.nome, "tipo": a.tipo,
                     "mensagem": a.mensagem, "data": iso(a.data),
                     "cor": "vermelho" if a.tipo == "estoque_baixo" else "amarelo"} for a in alertas],
    }


# ---------------------------------------------------------------- tela: Produto
@api("GET")
def detalhe_produto(request, id_produto):
    p = produto_dict(buscar_produto(id_produto))
    p["proximos_vencimentos"] = lotes(id_produto=id_produto)
    movs = Estoque.objects.filter(produto_id=id_produto).order_by("-data", "-id_estoque")[:10]
    p["historico"] = [{"id_estoque": m.id_estoque, "tipo_movimentacao": m.tipo_movimentacao, "quantidade": m.quantidade,
                       "motivo": m.motivo, "data": iso(m.data)} for m in movs]
    return p


@api("POST")
def registrar_entrada(request, id_produto):
    p = buscar_produto(id_produto)
    d = corpo(request)
    aplicar_entrada(p, c_int(d, "quantidade", minimo=1), c_str(d, "motivo"), c_str(d, "lote", obrig=False),
                    c_data(d, "data_validade", obrig=False))
    sincronizar_alertas()
    return produto_dict(buscar_produto(id_produto)), 201


@api("POST")
def registrar_saida(request, id_produto):
    p = buscar_produto(id_produto)
    d = corpo(request)
    aplicar_saida(p, c_int(d, "quantidade", minimo=1), c_str(d, "motivo"))
    sincronizar_alertas()
    return produto_dict(buscar_produto(id_produto)), 201


# ---------------------------------------------------------------- tela: Compras
def situacao_compra(c: Compra) -> str:
    return "recebido" if c.data_recebimento else "pendente"


def compra_dict(c: Compra) -> dict:
    return {"id_compra": c.id_compra, "data_pedido": iso(c.data_pedido),
            "data_recebimento": iso(c.data_recebimento) if c.data_recebimento else None,
            "fornecedor": c.fornecedor.nome, "valor_total": float(c.valor_total), "situacao": situacao_compra(c),
            "itens": [{"id_produto": i.produto_id, "produto": i.produto.nome, "quantidade": i.quantidade,
                       "custo_unitario": float(i.custo_unitario)} for i in sorted(c.itens.all(), key=lambda i: i.id_item_compra)]}


@api("GET", "POST")
def compras(request):
    if request.method == "GET":
        return [compra_dict(c) for c in Compra.objects.select_related("fornecedor").prefetch_related("itens__produto").order_by("-data_pedido", "-id_compra")]
    # POST: registra Compra + ItemCompra (situação: pendente)
    d = corpo(request)
    fornecedor = c_str(d, "fornecedor")
    dia = c_data(d, "data_pedido", obrig=False)
    data_pedido = datetime.combine(dia, datetime.min.time()) if dia else agora()
    itens = []
    for it in c_lista(d, "itens"):
        itens.append((buscar_produto(c_int(it, "id_produto")), c_int(it, "quantidade", minimo=1), c_dinheiro(it, "custo_unitario")))
    total = sum((q * custo for _, q, custo in itens), Decimal("0"))
    forn = Fornecedor.objects.filter(nome__iexact=fornecedor).first() or Fornecedor.objects.create(nome=fornecedor)
    c = Compra.objects.create(data_pedido=data_pedido, fornecedor=forn, valor_total=total)
    for p, q, custo in itens:
        ItemCompra.objects.create(compra=c, produto=p, quantidade=q, custo_unitario=custo)
        Produto.objects.filter(pk=p.pk, fornecedor__isnull=True).update(fornecedor=forn)  # fornecedor padrão do produto
    return compra_dict(c), 201


@api("POST")
def receber_compra(request, id_compra):
    """Marca a compra como recebida e dá entrada no estoque (motivo 'compra').
    Produtos perecíveis exigem lote/validade em `validades`."""
    c = Compra.objects.select_related("fornecedor").filter(pk=id_compra).first()
    if not c:
        raise ApiError(404, "Compra não encontrada")
    if c.data_recebimento:
        raise ApiError(409, "Compra já recebida")
    val = {}
    for v in c_lista(corpo(request), "validades", obrig=False):
        val[c_int(v, "id_produto")] = (c_str(v, "lote", obrig=False), c_data(v, "data_validade"))
    for it in c.itens.select_related("produto").order_by("id_item_compra"):
        lote, data_validade = val.get(it.produto_id, (None, None))
        aplicar_entrada(it.produto, it.quantidade, "compra", lote, data_validade)
    Compra.objects.filter(pk=c.pk).update(data_recebimento=agora())
    sincronizar_alertas()
    return compra_dict(Compra.objects.select_related("fornecedor").get(pk=c.pk))


# ---------------------------------------------------------------- tela: Validades
@api("GET")
def validades(request):
    return {"vencendo_em_breve": lotes(proximos=True), "outros_lotes": lotes(proximos=False)}


# ---------------------------------------------------------------- tela: Relatório diário
@api("GET")
def relatorio_diario(request):
    sincronizar_alertas()
    por_forma = {"dinheiro": 0.0, "pix": 0.0, "cartao": 0.0}
    for r in Venda.objects.filter(data_hora__date=hoje()).values("forma_pagamento").annotate(t=Sum("valor_total")):
        por_forma[r["forma_pagamento"]] = float(r["t"])
    mais_vendidos = (ItemVenda.objects.filter(venda__data_hora__date=hoje())
                     .values("produto__nome").annotate(q=Sum("quantidade"))
                     .order_by("-q", "produto__nome")[:3])
    return {
        "data": hoje().isoformat(),
        "vendas_total": round(sum(por_forma.values()), 2),
        "por_forma_pagamento": {k: round(v, 2) for k, v in por_forma.items()},
        "produtos_mais_vendidos": [{"produto": r["produto__nome"], "quantidade": r["q"]} for r in mais_vendidos],
        "alertas": {
            "produtos_abaixo_do_minimo": contar_baixos(),
            "produtos_proximos_do_vencimento": len({l["id_produto"] for l in lotes(proximos=True)}),
        },
    }
