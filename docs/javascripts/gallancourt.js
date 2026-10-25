/* Comportamentos da wiki de Gallancourt.
 *
 * 1. Tabela de NPCs (personagens/index.md): ordenar clicando no cabeçalho, filtrar por coluna
 *    (listas no cabeçalho) e filtrar por texto livre.
 * 2. Páginas com abas: um link para uma seção (#ancora) abre a aba que a contém.
 */
(function () {
  "use strict";

  // Colunas da tabela que ganham uma lista de filtro no cabeçalho (pelo texto do <th>).
  var COLUNAS_COM_FILTRO = ["Título", "Raça", "Cidade", "Afiliação"];
  var COLUNAS_SEM_ORDEM = ["Retrato"];

  function normalizar(texto) {
    return (texto || "")
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .toLowerCase()
      .trim();
  }

  function textoCelula(linha, indice) {
    var celula = linha.cells[indice];
    return celula ? celula.textContent.trim() : "";
  }

  function montarTabelaNpcs(raiz) {
    var tabela = raiz.querySelector(".npc-tabela table");
    if (!tabela || tabela.dataset.pronta) return;
    tabela.dataset.pronta = "1";

    var corpo = tabela.tBodies[0];
    var linhas = Array.prototype.slice.call(corpo.rows);
    var cabecalhos = Array.prototype.slice.call(tabela.tHead.rows[0].cells);
    var busca = raiz.querySelector(".npc-busca");
    var contagem = raiz.querySelector(".npc-contagem");
    var filtros = {}; // índice da coluna -> valor escolhido
    var ordem = { indice: -1, direcao: 1 };

    function aplicarFiltros() {
      var termo = normalizar(busca ? busca.value : "");
      var visiveis = 0;
      linhas.forEach(function (linha) {
        var ok = !termo || normalizar(linha.textContent).indexOf(termo) !== -1;
        Object.keys(filtros).forEach(function (indice) {
          if (ok && filtros[indice] && textoCelula(linha, +indice) !== filtros[indice]) ok = false;
        });
        linha.hidden = !ok;
        if (ok) visiveis++;
      });
      if (contagem) {
        contagem.textContent = visiveis === linhas.length
          ? linhas.length + " NPCs"
          : visiveis + " de " + linhas.length + " NPCs";
      }
    }

    function ordenar(indice) {
      ordem.direcao = ordem.indice === indice ? -ordem.direcao : 1;
      ordem.indice = indice;
      linhas.sort(function (a, b) {
        var va = textoCelula(a, indice), vb = textoCelula(b, indice);
        // "—" (sem dado) vai sempre para o fim
        if (va === "—" && vb !== "—") return 1;
        if (vb === "—" && va !== "—") return -1;
        return va.localeCompare(vb, "pt-BR", { sensitivity: "base" }) * ordem.direcao;
      });
      linhas.forEach(function (linha) { corpo.appendChild(linha); });
      cabecalhos.forEach(function (th, i) {
        th.setAttribute("aria-sort", i === indice ? (ordem.direcao === 1 ? "ascending" : "descending") : "none");
      });
    }

    cabecalhos.forEach(function (th, indice) {
      var rotulo = th.textContent.trim();
      th.textContent = "";

      if (COLUNAS_SEM_ORDEM.indexOf(rotulo) === -1) {
        var botao = document.createElement("button");
        botao.type = "button";
        botao.className = "npc-ordenar";
        botao.textContent = rotulo;
        botao.title = "Ordenar por " + rotulo;
        botao.addEventListener("click", function () { ordenar(indice); });
        th.appendChild(botao);
        th.setAttribute("aria-sort", "none");
      } else {
        var span = document.createElement("span");
        span.className = "npc-rotulo";
        span.textContent = rotulo;
        th.appendChild(span);
      }

      if (COLUNAS_COM_FILTRO.indexOf(rotulo) !== -1) {
        var valores = {};
        linhas.forEach(function (linha) { valores[textoCelula(linha, indice)] = true; });
        var lista = document.createElement("select");
        lista.className = "npc-filtro";
        lista.setAttribute("aria-label", "Filtrar por " + rotulo);
        lista.appendChild(new Option("Todos", ""));
        Object.keys(valores)
          .sort(function (a, b) { return a.localeCompare(b, "pt-BR"); })
          .forEach(function (valor) { lista.appendChild(new Option(valor, valor)); });
        lista.addEventListener("change", function () {
          filtros[indice] = lista.value;
          aplicarFiltros();
        });
        th.appendChild(lista);
      }
    });

    if (busca) busca.addEventListener("input", aplicarFiltros);
    aplicarFiltros();
  }

  function abrirAbaDaAncora() {
    if (!location.hash) return;
    var alvo = document.getElementById(decodeURIComponent(location.hash.slice(1)));
    var bloco = alvo && alvo.closest(".tabbed-block");
    if (!bloco) return;
    var conjunto = bloco.closest(".tabbed-set");
    var indice = Array.prototype.indexOf.call(bloco.parentElement.children, bloco);
    var entrada = conjunto.querySelectorAll(":scope > input")[indice];
    if (entrada) {
      entrada.checked = true;
      alvo.scrollIntoView();
    }
  }

  function iniciar() {
    montarTabelaNpcs(document);
    abrirAbaDaAncora();
  }

  // Compatível com a navegação instantânea do Material (document$), se for ativada um dia.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(iniciar);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
  window.addEventListener("hashchange", abrirAbaDaAncora);
})();
