CREATE SCHEMA IF NOT EXISTS config;
CREATE SCHEMA IF NOT EXISTS compras;
CREATE SCHEMA IF NOT EXISTS vendas;
CREATE SCHEMA IF NOT EXISTS estoque;

-- 1. Tabelas Independentes (Não possuem Chaves Estrangeiras)
CREATE TABLE IF NOT EXISTS config.roles(
    roles_id SERIAL NOT NULL,
    perfil VARCHAR(20) NOT NULL,
    CONSTRAINT roles_pk PRIMARY KEY (roles_id)
);

CREATE TABLE IF NOT EXISTS estoque.categories(
    categories_id SERIAL NOT NULL,
    nome VARCHAR(255) NOT NULL,
    CONSTRAINT categories_pk PRIMARY KEY (categories_id)
);

CREATE TABLE IF NOT EXISTS compras.suppliers (
    supplier_id UUID DEFAULT gen_random_uuid() NOT NULL,
    nome VARCHAR(255) NOT NULL,
    prazo_entrega_dias INTEGER NOT NULL DEFAULT 1,
    CONSTRAINT suppliers_pk PRIMARY KEY (supplier_id)
);

-- 2. Tabelas Dependentes Nível 1
CREATE TABLE IF NOT EXISTS config.users(
    users_id UUID DEFAULT gen_random_uuid() NOT NULL,
    roles_id INTEGER NOT NULL, -- Coluna física adicionada
    nome VARCHAR(255) NOT NULL,
    login VARCHAR(20) UNIQUE NOT NULL,
    senha VARCHAR(255) NOT NULL, -- Ajustado para suportar o bcrypt
    CONSTRAINT users_pk PRIMARY KEY (users_id),
    CONSTRAINT perfil_fk FOREIGN KEY (roles_id) REFERENCES config.roles (roles_id)
);

CREATE TABLE IF NOT EXISTS compras.suppliers_tel (
    supplier_telephone_id SERIAL NOT NULL,
    supplier_id UUID NOT NULL, -- Coluna física adicionada
    telefone VARCHAR(20) UNIQUE NOT NULL, -- Telefone costuma ter traços, melhor VARCHAR
    CONSTRAINT suppliers_tel_pk PRIMARY KEY (supplier_telephone_id),
    CONSTRAINT fornecedor_tel_fk FOREIGN KEY (supplier_id) REFERENCES compras.suppliers(supplier_id)
);

CREATE TABLE IF NOT EXISTS compras.entry (
    entry_id UUID DEFAULT gen_random_uuid() NOT NULL,
    supplier_id UUID NOT NULL, -- Coluna física adicionada
    data_compra TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valor_total DECIMAL(10,2) NOT NULL,
    CONSTRAINT entry_pk PRIMARY KEY (entry_id),
    CONSTRAINT fornecedor_entry_fk FOREIGN KEY (supplier_id) REFERENCES compras.suppliers(supplier_id)
);

CREATE TABLE IF NOT EXISTS estoque.products(
    products_id SERIAL NOT NULL,
    categories_id INTEGER NOT NULL, -- Coluna física adicionada
    supplier_id UUID NOT NULL,      -- Coluna física adicionada
    nome VARCHAR(255) NOT NULL,
    sku VARCHAR(100) NOT NULL UNIQUE,
    estoque_minimo INTEGER NOT NULL DEFAULT 5,
    preco_unitario DECIMAL(10,2) NOT NULL,
    CONSTRAINT products_pk PRIMARY KEY (products_id),
    CONSTRAINT categoria_fk FOREIGN KEY (categories_id) REFERENCES estoque.categories(categories_id),
    CONSTRAINT fornecedor_prod_fk FOREIGN KEY (supplier_id) REFERENCES compras.suppliers (supplier_id)
);

-- 3. Tabelas Dependentes Nível 2
CREATE TABLE IF NOT EXISTS compras.items_entry(
    items_entry_id SERIAL NOT NULL,
    entry_id UUID NOT NULL,        -- Coluna física adicionada
    products_id INTEGER NOT NULL,  -- Coluna física adicionada
    quantidade INTEGER NOT NULL,
    valor_unitario DECIMAL(10,2) NOT NULL,
    CONSTRAINT items_entry_pk PRIMARY KEY (items_entry_id),
    CONSTRAINT entrada_fk FOREIGN KEY (entry_id) REFERENCES compras.entry (entry_id) ON DELETE CASCADE,
    CONSTRAINT produto_entry_fk FOREIGN KEY (products_id) REFERENCES estoque.products (products_id)
);

CREATE TABLE IF NOT EXISTS estoque.batches (
    batches_id SERIAL NOT NULL,
    products_id INTEGER NOT NULL, -- Coluna física adicionada
    data_validade DATE NOT NULL,
    quantidade_atual INTEGER NOT NULL,
    data_entrada TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT batches_pk PRIMARY KEY (batches_id), -- Corrigido de FOREIGN KEY para PRIMARY KEY
    CONSTRAINT produto_batch_fk FOREIGN KEY (products_id) REFERENCES estoque.products (products_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vendas.sales (
    sales_id UUID DEFAULT gen_random_uuid() NOT NULL,
    users_id UUID NOT NULL, -- Coluna física adicionada
    data_venda TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valor_total DECIMAL(10,2) NOT NULL,
    CONSTRAINT sales_pk PRIMARY KEY (sales_id),
    CONSTRAINT usuario_sale_fk FOREIGN KEY (users_id) REFERENCES config.users (users_id)
);

CREATE TABLE IF NOT EXISTS vendas.items_sale (
    items_sale_id SERIAL NOT NULL,
    sales_id UUID NOT NULL, -- Coluna física adicionada
    sku VARCHAR(100) NOT NULL, -- Referenciando o SKU da tabela products
    quantidade INTEGER NOT NULL,
    preco_unitario DECIMAL(10,2) NOT NULL,
    preco_quantidade DECIMAL(10,2) GENERATED ALWAYS AS (quantidade * preco_unitario) STORED, -- Cálculo automático
    CONSTRAINT items_sale_pk PRIMARY KEY (items_sale_id),
    CONSTRAINT venda_fk FOREIGN KEY (sales_id) REFERENCES vendas.sales(sales_id) ON DELETE CASCADE,
    CONSTRAINT produto_sale_fk FOREIGN KEY (sku) REFERENCES estoque.products(sku)
);