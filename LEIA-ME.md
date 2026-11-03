# Mercado Cesar — como rodar

Duas pastas: `backend_django/` (API) e `frontend/` (telas). Rode as duas ao mesmo tempo, em dois terminais.

## 1) Banco PostgreSQL (uma vez)
O banco agora é o do `mercadinhoSeuJoao.sql` (PostgreSQL, com schemas config/compras/vendas/estoque).
Crie um banco vazio e, se precisar, configure as variáveis (padrões entre parênteses):
    createdb mercado
    MERCADO_DB (mercado)  MERCADO_DB_USER (postgres)  MERCADO_DB_PASSWORD (postgres)  MERCADO_DB_HOST (127.0.0.1)  MERCADO_DB_PORT (5432)

## 1b) Back end (terminal 1)
    cd backend_django
    python -m pip install -r requirements.txt
    python manage.py migrate        # roda api/sql/01 + 02 (cria tabelas) E cria perfis, categorias e usuários padrão
    python manage.py runserver      # API em http://127.0.0.1:8000

## 2) Front end (terminal 2)
    cd frontend
    python -m http.server 5500

Abra http://127.0.0.1:5500 no navegador.

## Logins criados pela migration 0002
| usuário | senha      | perfil        |
|---------|------------|---------------|
| cesar   | mercado123 | administrador |
| caixa   | caixa123   | funcionario   |

Troque essas senhas antes de usar de verdade.

## Se algo der errado
- "Não consegui falar com o servidor": o back end não está rodando, ou o endereço em `frontend/config.js` está diferente.
- Tela de produtos vazia: normal no começo. Cadastre categorias/produtos e dê entrada no estoque.
- Login: a API devolve um token (vale 12 h) que o front envia em todas as chamadas. Token vencido volta para a tela de login.

## Como o front usa a API
- `frontend/style.css` é o CSS original da sua amiga, sem alterações. Só foi acrescentado, no final, o bloco da tela de login.
- `frontend/app.js` mantém as telas e as regras de inteligência originais. Os dados vêm da API (`api.js`).
- Venda média/dia, última venda, custo e fornecedor são calculados a partir das vendas e compras do back end (não existem como campo no banco).
- Os custos só aparecem depois que houver pedidos de compra registrados.

## Banco de dados (SQL integrado)
- `api/sql/01_mercadinhoSeuJoao.sql` é o SQL original, sem alterações. `api/sql/02_ajustes.sql` acrescenta o que o sistema precisa:
  `products.estoque_atual` (saldo) e `perecivel`, `supplier_id` opcional, `batches.lote`, `entry.numero` (nº do pedido) e `data_recebimento`
  (vazio = pendente), `sales.forma_pagamento`, e as tabelas `estoque.movements` e `estoque.alerts`.
- Os models (`api/models.py`) são `managed=False` e apontam para essas tabelas; os nomes usados pela API/front (`id_produto`, `preco_venda`...) são mapeados com `db_column`.
- Lotes (`batches`) existem só para produtos perecíveis (a validade é obrigatória no SQL). O item de venda referencia o produto pelo SKU, como no SQL.
- Para recomeçar do zero: apague o banco, crie de novo e rode `migrate`.
