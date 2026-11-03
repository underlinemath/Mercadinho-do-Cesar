-- Ajustes sobre o 01_mercadinhoSeuJoao.sql (que fica intacto), para o sistema funcionar.
-- Produtos: estoque atual (saldo) e perecível; fornecedor passa a ser opcional (produto novo ainda não tem compra).
ALTER TABLE estoque.products ADD COLUMN IF NOT EXISTS estoque_atual INTEGER NOT NULL DEFAULT 0 CHECK (estoque_atual >= 0);
ALTER TABLE estoque.products ADD COLUMN IF NOT EXISTS perecivel BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE estoque.products ALTER COLUMN supplier_id DROP NOT NULL;

-- Lotes (só de produtos perecíveis): nome do lote.
ALTER TABLE estoque.batches ADD COLUMN IF NOT EXISTS lote VARCHAR(50);
CREATE INDEX IF NOT EXISTS batches_prod_idx ON estoque.batches (products_id);

-- Compras: número sequencial do pedido e data de recebimento (NULL = pendente).
ALTER TABLE compras.entry ADD COLUMN IF NOT EXISTS numero SERIAL;
CREATE UNIQUE INDEX IF NOT EXISTS entry_numero_uk ON compras.entry (numero);
ALTER TABLE compras.entry ADD COLUMN IF NOT EXISTS data_recebimento TIMESTAMP;

-- Vendas: forma de pagamento.
ALTER TABLE vendas.sales ADD COLUMN IF NOT EXISTS forma_pagamento VARCHAR(10) NOT NULL DEFAULT 'dinheiro'
    CHECK (forma_pagamento IN ('pix','dinheiro','cartao'));

-- Movimentações de estoque (entradas e saídas) e alertas.
CREATE TABLE IF NOT EXISTS estoque.movements (
    movements_id SERIAL PRIMARY KEY,
    products_id INTEGER NOT NULL REFERENCES estoque.products (products_id) ON DELETE CASCADE,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('entrada','saida')),
    quantidade INTEGER NOT NULL CHECK (quantidade > 0),
    motivo VARCHAR(100) NOT NULL,
    data TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS estoque.alerts (
    alerts_id SERIAL PRIMARY KEY,
    products_id INTEGER NOT NULL REFERENCES estoque.products (products_id) ON DELETE CASCADE,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('estoque_baixo','validade')),
    mensagem VARCHAR(255) NOT NULL,
    data TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(10) NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente','resolvido'))
);
