/* Roadmap embutido (ver admin/app.py rotas /api/roadmap e hooks/gallancourt.py — marcador
 * <!-- roadmap:lista --> trocado por uma raiz vazia) — widget que roda dentro da
 * `<div class="roadmap-painel ficha-personagem" data-roadmap>` de docs/roadmap/index.md, falando por
 * fetch() com a API (lê/escreve dados/roadmap.yml via admin/wiki_data.py, sem banco). Mesmo
 * esqueleto dos outros widgets do site (ficha-personagem.js, painel-iniciativa.js): busca ao
 * carregar, redesenha a partir da resposta.
 *
 * Em modo leitura (sem Modo Mestre), mostra só a tabela com busca. Em Modo Mestre: botão
 * "+ adicionar item", e cada linha ganha Editar/Apagar — tudo sem precisar de mkdocs build.
 *
 * A busca por texto nunca reconstrói o campo de busca (só a tabela/contagem), pelo mesmo motivo
 * já corrigido no seletor de catálogo de ficha-personagem.js: reconstruir o <input> a cada tecla
 * tira o foco e desmarca o que o usuário ainda está digitando.
 */
(function () {
  "use strict";

  var CLASSE_PRIORIDADE = { Alta: "alta", "Média": "media", Baixa: "baixa" };
  var CLASSE_STATUS = { Planejado: "planejado", "Em andamento": "andamento", "Concluído": "concluido" };

  function escapeHtml(valor) {
    return String(valor == null ? "" : valor)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function normalizar(texto) {
    return String(texto || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .trim();
  }

  function selo(texto, classes) {
    if (!texto) return "—";
    var classe = classes[texto] || "neutro";
    return '<span class="selo selo--' + classe + '">' + escapeHtml(texto) + "</span>";
  }

  function opcoes(lista, atual) {
    return lista.map(function (v) {
      return '<option value="' + escapeHtml(v) + '"' + (v === atual ? " selected" : "") + ">" + escapeHtml(v) + "</option>";
    }).join("");
  }

  function Widget(raiz) {
    this.raiz = raiz;
    this.itens = [];
    this.prioridades = [];
    this.tipos = [];
    this.statusOpcoes = [];
    this.autenticado = false;
    this.busca = "";
    this.editando = null; // null | "novo" | id numérico
    this.carregar();
  }

  Widget.prototype.carregar = function () {
    var self = this;
    Promise.all([
      fetch("/api/roadmap").then(function (r) { return r.json(); }),
      fetch("/api/auth/estado").then(function (r) { return r.json(); }).catch(function () { return { autenticado: false }; }),
    ]).then(function (resultados) {
      var roadmap = resultados[0], auth = resultados[1];
      self.itens = roadmap.itens || [];
      self.prioridades = roadmap.prioridades || [];
      self.tipos = roadmap.tipos || [];
      self.statusOpcoes = roadmap.status_opcoes || [];
      self.autenticado = !!auth.autenticado;
      self.renderizar();
    }).catch(function () {
      self.raiz.innerHTML = '<p class="aviso aviso--erro">Não foi possível carregar o roadmap.</p>';
    });
  };

  Widget.prototype.itensFiltrados = function () {
    var alvo = normalizar(this.busca);
    if (!alvo) return this.itens;
    return this.itens.filter(function (i) {
      return [i.item, i.prioridade, i.tipo, i.responsavel, i.status].some(function (campo) {
        return normalizar(campo).indexOf(alvo) !== -1;
      });
    });
  };

  Widget.prototype.linhaFormulario = function () {
    if (!this.autenticado || this.editando === null) return "";
    var item = this.editando === "novo" ? {} : (this.itens.filter(function (i) { return i.id === this.editando; }, this)[0] || {});
    return (
      '<form class="roadmap-form" data-form>' +
      '<label>O que falta fazer<textarea name="item" rows="2" required>' + escapeHtml(item.item) + "</textarea></label>" +
      '<div class="duas-colunas">' +
      '<label>Prioridade<select name="prioridade">' + opcoes(this.prioridades, item.prioridade) + "</select></label>" +
      '<label>Funcionalidade<select name="tipo">' + opcoes(this.tipos, item.tipo) + "</select></label>" +
      '<label>Status<select name="status">' + opcoes(this.statusOpcoes, item.status) + "</select></label>" +
      "</div>" +
      '<label>Responsável (opcional)<input type="text" name="responsavel" value="' + escapeHtml(item.responsavel) + '" placeholder="Deixe em branco se ainda ninguém começou"></label>' +
      '<div class="ficha-personagem__acoes-rodape">' +
      '<button type="submit" class="botao-principal">' + (this.editando === "novo" ? "Adicionar" : "Salvar") + "</button>" +
      '<button type="button" class="botao-secundario" data-acao="cancelar">Cancelar</button>' +
      "</div>" +
      "</form>"
    );
  };

  Widget.prototype.linhasTabela = function () {
    var self = this;
    var linhas = this.itensFiltrados();
    if (!linhas.length) {
      return '<tr><td colspan="' + (this.autenticado ? 6 : 5) + '" class="ajuda">Nada encontrado.</td></tr>';
    }
    return linhas.map(function (i) {
      var acoes = self.autenticado
        ? '<td class="acoes">' +
          '<button type="button" class="botao-link" data-acao="editar" data-id="' + i.id + '">Editar</button> ' +
          '<button type="button" class="botao-link botao-remover" data-acao="apagar" data-id="' + i.id + '">Apagar</button>' +
          "</td>"
        : "";
      return (
        "<tr>" +
        "<td>" + escapeHtml(i.item) + "</td>" +
        "<td>" + selo(i.prioridade, CLASSE_PRIORIDADE) + "</td>" +
        "<td>" + escapeHtml(i.tipo) + "</td>" +
        "<td>" + (i.responsavel ? escapeHtml(i.responsavel) : "—") + "</td>" +
        "<td>" + selo(i.status, CLASSE_STATUS) + "</td>" +
        acoes +
        "</tr>"
      );
    }).join("");
  };

  Widget.prototype.atualizarTabela = function () {
    var tbody = this.raiz.querySelector(".roadmap-tabela tbody");
    var contagem = this.raiz.querySelector(".roadmap-contagem");
    if (!tbody) return;
    tbody.innerHTML = this.linhasTabela();
    var total = this.itensFiltrados().length;
    if (contagem) contagem.textContent = total + (total === 1 ? " item" : " itens");
  };

  Widget.prototype.renderizar = function () {
    var self = this;
    var colunaAcoes = this.autenticado ? "<th></th>" : "";
    this.raiz.innerHTML =
      '<div class="roadmap-ferramentas">' +
      '<input type="search" class="roadmap-busca" placeholder="Filtrar por texto…" aria-label="Filtrar" value="' + escapeHtml(this.busca) + '">' +
      '<span class="roadmap-contagem" aria-live="polite"></span>' +
      (this.autenticado ? '<button type="button" class="botao-principal" data-acao="novo">+ adicionar item</button>' : "") +
      "</div>" +
      this.linhaFormulario() +
      '<div class="roadmap-tabela"><table><thead><tr>' +
      "<th>Item</th><th>Prioridade</th><th>Funcionalidade</th><th>Responsável</th><th>Status</th>" + colunaAcoes +
      "</tr></thead><tbody>" + this.linhasTabela() + "</tbody></table></div>";

    this.raiz.querySelector(".roadmap-busca").addEventListener("input", function (e) {
      self.busca = e.target.value;
      self.atualizarTabela();
    });
    this.atualizarTabela();

    var botaoNovo = this.raiz.querySelector('[data-acao="novo"]');
    if (botaoNovo) botaoNovo.addEventListener("click", function () { self.editando = "novo"; self.renderizar(); });

    this.raiz.querySelectorAll('[data-acao="editar"]').forEach(function (botao) {
      botao.addEventListener("click", function () {
        self.editando = parseInt(botao.getAttribute("data-id"), 10);
        self.renderizar();
      });
    });
    this.raiz.querySelectorAll('[data-acao="apagar"]').forEach(function (botao) {
      botao.addEventListener("click", function () { self.apagar(parseInt(botao.getAttribute("data-id"), 10)); });
    });
    var cancelar = this.raiz.querySelector('[data-acao="cancelar"]');
    if (cancelar) cancelar.addEventListener("click", function () { self.editando = null; self.renderizar(); });

    var formulario = this.raiz.querySelector("[data-form]");
    if (formulario) {
      formulario.addEventListener("submit", function (e) {
        e.preventDefault();
        var dados = {
          item: formulario.item.value.trim(),
          prioridade: formulario.prioridade.value,
          tipo: formulario.tipo.value,
          status: formulario.status.value,
          responsavel: formulario.responsavel.value.trim(),
        };
        if (self.editando === "novo") self.criar(dados);
        else self.salvar(self.editando, dados);
      });
    }
  };

  Widget.prototype.criar = function (dados) {
    var self = this;
    fetch("/api/roadmap", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(dados) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.erro) { window.alert(d.erro); return; }
        self.itens = d.itens;
        self.editando = null;
        self.renderizar();
      });
  };

  Widget.prototype.salvar = function (id, dados) {
    var self = this;
    fetch("/api/roadmap/" + id, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(dados) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.erro) { window.alert(d.erro); return; }
        self.itens = d.itens;
        self.editando = null;
        self.renderizar();
      });
  };

  Widget.prototype.apagar = function (id) {
    if (!window.confirm("Apagar este item do roadmap?")) return;
    var self = this;
    fetch("/api/roadmap/" + id, { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.erro) { window.alert(d.erro); return; }
        self.itens = d.itens;
        self.renderizar();
      });
  };

  function iniciar() {
    document.querySelectorAll(".roadmap-painel[data-roadmap]").forEach(function (raiz) {
      if (raiz.dataset.montado) return;
      raiz.dataset.montado = "1";
      new Widget(raiz);
    });
  }

  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(iniciar);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
