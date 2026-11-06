/* Encontro planejado (ver admin/encontro_api.py e hooks/gallancourt.py::_encontro_dinamico) —
 * widget que roda dentro da `<div class="encontro-planejado ficha-personagem" data-pagina="...">`
 * na aba "NPCs" de cada página de sessão, falando por fetch() com a API do banco (admin/app.py,
 * rotas /api/encontros/...). Mesmo esqueleto de combate.js: busca ao carregar, redesenha a cada
 * ação a partir da resposta. Só prepara a lista de participantes — o combate em si (iniciativa,
 * PV, condições) só nasce quando a aba Combat Tracker chama "Iniciar combate" a partir de um
 * destes rascunhos (ver combate.js).
 */
(function () {
  "use strict";

  var TIPOS_ATOR = ["monstro", "npc", "jogador"];
  var ROTULOS_TIPO_ATOR = { monstro: "Monstro", npc: "NPC", jogador: "Jogador" };

  function escapeHtml(valor) {
    return String(valor == null ? "" : valor)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function Widget(raiz) {
    this.raiz = raiz;
    this.pagina = raiz.getAttribute("data-pagina");
    this.encontros = [];
    this.autenticado = false;
    this.aberto = null; // id do encontro expandido
    this.novoNome = "";
    this.busca = null; // { encontroId, tipo, q, resultados, nomeExibicao }
    this.ligarEventos();
    this.carregar();
  }

  Widget.prototype._url = function (caminho) {
    return "/api/encontros/" + encodeURIComponent(this.pagina) + (caminho || "");
  };

  Widget.prototype.carregar = function () {
    var self = this;
    Promise.all([
      fetch(this._url()).then(function (r) { return r.json(); }),
      fetch("/api/auth/estado").then(function (r) { return r.json(); }).catch(function () { return { autenticado: false }; }),
    ]).then(function (resultados) {
      self.encontros = resultados[0].encontros || [];
      self.autenticado = !!resultados[1].autenticado;
      self.renderizar();
    }).catch(function (erro) {
      self.raiz.innerHTML = '<p class="ajuda">⚠️ Não consegui falar com o Painel do Mestre. ' +
        "Confirme que ele está rodando e recarregue a página. <small>(" + escapeHtml(erro && erro.message) + ")</small></p>";
    });
  };

  Widget.prototype.chamar = function (metodo, caminho, corpo) {
    var self = this;
    var opcoes = { method: metodo };
    if (corpo !== undefined) {
      opcoes.headers = { "Content-Type": "application/json" };
      opcoes.body = JSON.stringify(corpo);
    }
    return fetch(caminho, opcoes)
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, dados: d }; }); })
      .then(function (res) {
        if (!res.ok || res.dados.erro) { window.alert(res.dados.erro || "Não deu certo."); return null; }
        return res.dados;
      })
      .catch(function (erro) { window.alert("Erro: " + erro.message); return null; });
  };

  Widget.prototype.renderizar = function () {
    if (!this.autenticado && this.encontros.length === 0) {
      this.raiz.innerHTML = '<p class="ajuda">Nenhum encontro planejado nesta sessão.</p>';
      return;
    }
    var self = this;
    var lista = this.encontros.map(function (e) { return self._cartaoEncontro(e); }).join("");
    this.raiz.innerHTML =
      '<div class="encontro-planejado__lista">' + (lista || '<p class="ajuda">Nenhum encontro planejado ainda.</p>') + "</div>" +
      (this.autenticado ? this._formNovoEncontro() : "");
  };

  Widget.prototype._formNovoEncontro = function () {
    return (
      '<div class="encontro-planejado__novo">' +
      '<input type="text" class="input-medio" placeholder="Nome do encontro (ex.: Emboscada na ponte)" ' +
      'value="' + escapeHtml(this.novoNome) + '" data-acao="novo-encontro-nome">' +
      '<button type="button" class="botao-secundario" data-acao="criar-encontro">+ novo encontro</button>' +
      "</div>"
    );
  };

  Widget.prototype._cartaoEncontro = function (e) {
    var aberto = this.aberto === e.id;
    var self = this;
    var participantes = e.participantes.map(function (p) {
      return (
        '<li class="encontro-planejado__participante">' +
        '<span class="pilula">' + escapeHtml(ROTULOS_TIPO_ATOR[p.tipo] || p.tipo) + "</span> " +
        escapeHtml(p.nome) +
        (self.autenticado
          ? ' <button type="button" class="botao-remover" data-acao="remover-planejado" data-participante="' + p.id + '" title="Remover">×</button>'
          : "") +
        "</li>"
      );
    }).join("");
    return (
      '<div class="encontro-planejado__cartao">' +
      '<div class="encontro-planejado__cabecalho" data-acao="abrir-encontro" data-encontro="' + e.id + '">' +
      '<strong>' + escapeHtml(e.nome) + "</strong> " +
      '<span class="ajuda">(' + e.participantes.length + " participante" + (e.participantes.length === 1 ? "" : "s") + ")</span>" +
      (this.autenticado
        ? ' <button type="button" class="botao-remover" data-acao="excluir-encontro" data-encontro="' + e.id + '" title="Excluir encontro">× excluir</button>'
        : "") +
      "</div>" +
      (aberto
        ? '<ul class="encontro-planejado__participantes">' + (participantes || '<li class="ajuda">Nenhum participante ainda.</li>') + "</ul>" +
          (this.autenticado ? this._formBusca(e.id) : "")
        : "") +
      "</div>"
    );
  };

  Widget.prototype._formBusca = function (encontroId) {
    var b = this.busca && this.busca.encontroId === encontroId ? this.busca : null;
    if (!b) {
      return '<button type="button" class="botao-secundario" data-acao="abrir-busca-planejado" data-encontro="' + encontroId + '">+ adicionar participante</button>';
    }
    var opcoesTipo = TIPOS_ATOR.map(function (t) {
      return '<option value="' + t + '"' + (t === b.tipo ? " selected" : "") + ">" + ROTULOS_TIPO_ATOR[t] + "</option>";
    }).join("");
    var linhas = (b.resultados || []).map(function (p) {
      return p.fichas.map(function (f) {
        var rotulo = f.is_base ? p.nome : p.nome + " (" + f.rotulo + ")";
        var info = f.cr ? "CR " + f.cr : (f.nivel != null ? "Nível " + f.nivel : "");
        return (
          "<tr><td>" + escapeHtml(rotulo) + "</td><td>" + escapeHtml(info) + "</td>" +
          '<td><button type="button" class="botao-secundario" data-acao="usar-busca-planejado" data-ficha="' + f.id + '">adicionar</button></td></tr>'
        );
      }).join("");
    }).join("");
    return (
      '<div class="encontro-planejado__busca">' +
      '<div class="combate-painel__busca-topo">' +
      '<select data-acao="tipo-busca-planejado">' + opcoesTipo + "</select>" +
      '<input type="search" placeholder="Buscar por nome…" value="' + escapeHtml(b.q || "") + '" data-acao="q-busca-planejado" autofocus>' +
      '<input type="text" class="input-medio" placeholder="Nome de exibição (opcional, ex.: Goblin 1)" value="' + escapeHtml(b.nomeExibicao || "") + '" data-acao="nome-busca-planejado">' +
      '<button type="button" class="botao-remover" data-acao="fechar-busca-planejado" title="Fechar">× Fechar</button>' +
      "</div>" +
      (linhas
        ? '<table class="ficha-personagem__picker-tabela"><thead><tr><th>Nome</th><th>Nível/CR</th><th></th></tr></thead><tbody>' + linhas + "</tbody></table>"
        : '<p class="ajuda">Nada encontrado.</p>') +
      "</div>"
    );
  };

  Widget.prototype._buscar = function () {
    var self = this;
    var b = this.busca;
    fetch("/api/personagens-busca?tipo=" + encodeURIComponent(b.tipo) + "&q=" + encodeURIComponent(b.q || ""))
      .then(function (r) { return r.json(); })
      .then(function (d) { b.resultados = d.itens || []; self.renderizar(); });
  };

  Widget.prototype.ligarEventos = function () {
    var self = this;

    this.raiz.addEventListener("input", function (ev) {
      var alvo = ev.target;
      if (alvo.matches("[data-acao='novo-encontro-nome']")) {
        self.novoNome = alvo.value;
      } else if (alvo.matches("[data-acao='q-busca-planejado']")) {
        self.busca.q = alvo.value;
        self._buscar();
      } else if (alvo.matches("[data-acao='nome-busca-planejado']")) {
        self.busca.nomeExibicao = alvo.value;
      } else {
        return;
      }
    });

    this.raiz.addEventListener("change", function (ev) {
      if (ev.target.matches("[data-acao='tipo-busca-planejado']")) {
        self.busca.tipo = ev.target.value;
        self._buscar();
      }
    });

    this.raiz.addEventListener("click", function (ev) {
      var cabecalho = ev.target.closest("[data-acao='abrir-encontro']");
      if (cabecalho && !ev.target.closest("button")) {
        var id = parseInt(cabecalho.getAttribute("data-encontro"), 10);
        self.aberto = self.aberto === id ? null : id;
        self.busca = null;
        self.renderizar();
        return;
      }

      var botao = ev.target.closest("button[data-acao]");
      if (!botao) return;
      var acao = botao.getAttribute("data-acao");
      var encontroId = botao.getAttribute("data-encontro");

      if (acao === "criar-encontro") {
        if (!self.novoNome.trim()) return;
        self.chamar("POST", self._url(), { nome: self.novoNome }).then(function (dados) {
          if (!dados) return;
          self.novoNome = "";
          self.carregar();
        });
      } else if (acao === "excluir-encontro") {
        if (!window.confirm("Excluir este encontro planejado?")) return;
        self.chamar("DELETE", "/api/encontros/" + encontroId).then(function () { self.carregar(); });
      } else if (acao === "abrir-busca-planejado") {
        self.busca = { encontroId: parseInt(encontroId, 10), tipo: "monstro", q: "", resultados: [], nomeExibicao: "" };
        self.renderizar();
      } else if (acao === "fechar-busca-planejado") {
        self.busca = null;
        self.renderizar();
      } else if (acao === "usar-busca-planejado") {
        self.chamar("POST", "/api/encontros/" + self.busca.encontroId + "/participantes", {
          ficha_id: botao.getAttribute("data-ficha"),
          nome_exibicao: self.busca.nomeExibicao,
        }).then(function (dados) {
          if (!dados) return;
          self.busca = null;
          self.carregar();
        });
      } else if (acao === "remover-planejado") {
        self.chamar("DELETE", "/api/encontros/participantes/" + botao.getAttribute("data-participante")).then(function () { self.carregar(); });
      }
    });
  };

  function iniciar() {
    document.querySelectorAll(".encontro-planejado[data-pagina]").forEach(function (raiz) {
      new Widget(raiz);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
