// Camada de comunicação com o back end Django (JSON).
const Auth = {
  KEY: "mercado_cesar_usuario",
  get() { try { return JSON.parse(localStorage.getItem(this.KEY)); } catch (e) { return null; } },
  set(u) { try { localStorage.setItem(this.KEY, JSON.stringify(u)); } catch (e) {} },
  clear() { try { localStorage.removeItem(this.KEY); } catch (e) {} }
};

async function request(method, path, body) {
  let res;
  try {
    res = await fetch(window.API_URL + path, {
      method,
      headers: Object.assign(body ? { "Content-Type": "application/json" } : {},
        (Auth.get() && Auth.get().token) ? { Authorization: "Bearer " + Auth.get().token } : {}),
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (e) {
    throw new Error("Não consegui falar com o servidor. Confira se o back end está rodando em " + window.API_URL);
  }
  let data = null;
  try { data = await res.json(); } catch (e) {}
  if (res.status === 401 && path !== "/login") {   // token vencido/inválido: volta para o login
    Auth.clear();
    if (typeof showLogin === "function") showLogin();
  }
  if (!res.ok) {
    const err = new Error((data && data.detail) || "Erro " + res.status);
    err.status = res.status;
    throw err;
  }
  return data;
}

const API = {
  login: (login, senha) => request("POST", "/login", { login, senha }),
  dashboard: () => request("GET", "/dashboard"),
  produtos: (nome) => request("GET", "/produtos" + (nome ? "?nome=" + encodeURIComponent(nome) : "")),
  produto: (id) => request("GET", "/produtos/" + id),
  produtoPorSku: (sku) => request("GET", "/produtos/sku/" + encodeURIComponent(sku)),
  criarProduto: (d) => request("POST", "/produtos", d),
  entrada: (id, d) => request("POST", `/produtos/${id}/entrada`, d),
  saida: (id, d) => request("POST", `/produtos/${id}/saida`, d),
  categorias: () => request("GET", "/categorias"),
  criarCategoria: (nome) => request("POST", "/categorias", { nome }),
  vendas: () => request("GET", "/vendas"),
  criarVenda: (d) => request("POST", "/vendas", d),
  compras: () => request("GET", "/compras"),
  criarCompra: (d) => request("POST", "/compras", d),
  receberCompra: (id, d) => request("POST", `/compras/${id}/receber`, d || {}),
  validades: () => request("GET", "/validades"),
  relatorio: () => request("GET", "/relatorio-diario")
};
