/* Comportamentos da wiki de Gallancourt.
 *
 * 1. Tabela de NPCs (personagens/index.md): ordenar clicando no cabeçalho, filtrar por coluna
 *    (listas no cabeçalho) e filtrar por texto livre.
 * 2. Páginas com abas: um link para uma seção (#ancora) abre a aba que a contém.
 * 3. Índice (TOC) da página: só mostra os cabeçalhos da aba selecionada no momento — clicar num
 *    cabeçalho de outra aba, escondido, não rolava a página (a aba continuava fechada).
 * 4. Magias (magias/index.md e magias/por-classe/*.md): mesma ideia da tabela de NPCs, mas com
 *    uma barra de filtros fixa (fora das abas) controlando várias tabelas ao mesmo tempo — uma
 *    por aba de nível — e colunas de classificação (Ritual, Categoria, Tipo de Dano…) escondidas
 *    por CSS, usadas só pelos filtros, não pela ordenação por clique.
 */
(function () {
  "use strict";

  // Colunas da tabela que ganham uma lista de filtro no cabeçalho (pelo texto do <th>).
  var COLUNAS_COM_FILTRO = ["Título", "Raça", "Cidade", "Afiliação", "Situação"];
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
        return va.localeCompare(vb, "pt-BR", { sensitivity: "base", numeric: true }) * ordem.direcao;
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
          .sort(function (a, b) { return a.localeCompare(b, "pt-BR", { numeric: true }); })
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

  // Colunas da tabela de magias que ficam escondidas por CSS (nth-child(n+8) — ver extra.css) e
  // por isso não recebem botão de ordenação, só servem de alvo para os filtros da barra.
  var COLUNAS_MAGIA_SEM_ORDEM = [
    "Ritual", "Concentração", "Categoria", "Tipo de Dano", "Tipo de Alcance", "Área de Efeito",
  ];

  function prepararOrdenacaoMagia(tabela) {
    var corpo = tabela.tBodies[0];
    var linhas = Array.prototype.slice.call(corpo.rows);
    var cabecalhos = Array.prototype.slice.call(tabela.tHead.rows[0].cells);
    var ordem = { indice: -1, direcao: 1 };

    function ordenar(indice) {
      ordem.direcao = ordem.indice === indice ? -ordem.direcao : 1;
      ordem.indice = indice;
      linhas.sort(function (a, b) {
        var va = textoCelula(a, indice), vb = textoCelula(b, indice);
        if (va === "—" && vb !== "—") return 1;
        if (vb === "—" && va !== "—") return -1;
        return va.localeCompare(vb, "pt-BR", { sensitivity: "base", numeric: true }) * ordem.direcao;
      });
      linhas.forEach(function (linha) { corpo.appendChild(linha); });
      cabecalhos.forEach(function (th, i) {
        th.setAttribute("aria-sort", i === indice ? (ordem.direcao === 1 ? "ascending" : "descending") : "none");
      });
    }

    cabecalhos.forEach(function (th, indice) {
      var rotulo = th.textContent.trim();
      th.textContent = "";
      if (COLUNAS_MAGIA_SEM_ORDEM.indexOf(rotulo) === -1) {
        var botao = document.createElement("button");
        botao.type = "button";
        botao.className = "magia-ordenar";
        botao.textContent = rotulo;
        botao.title = "Ordenar por " + rotulo;
        botao.addEventListener("click", function () { ordenar(indice); });
        th.appendChild(botao);
        th.setAttribute("aria-sort", "none");
      } else {
        var span = document.createElement("span");
        span.className = "magia-rotulo";
        span.textContent = rotulo;
        th.appendChild(span);
      }
    });
  }

  function indiceColunaMagia(tabela, nomeColuna) {
    var ths = tabela.tHead.rows[0].cells;
    for (var i = 0; i < ths.length; i++) {
      if (ths[i].textContent.trim() === nomeColuna) return i;
    }
    return -1;
  }

  // Uma barra de filtros (busca + <select class="magia-filtro" data-coluna data-modo>) controla
  // todas as tabelas de magia da página (uma por aba de nível, em magias/index.md; uma só, em
  // magias/por-classe/*.md). data-modo="contem" faz busca por substring (coluna Classes, onde
  // cada célula lista vários valores); o padrão é igualdade exata.
  function montarPainelMagias(raiz) {
    var tabelas = Array.prototype.slice.call(raiz.querySelectorAll(".magia-tabela table"));
    if (!tabelas.length) return;
    tabelas.forEach(function (tabela) {
      if (tabela.dataset.pronta) return;
      tabela.dataset.pronta = "1";
      prepararOrdenacaoMagia(tabela);
    });

    var busca = raiz.querySelector(".magia-busca");
    var contagem = raiz.querySelector(".magia-contagem");
    if (contagem && contagem.dataset.pronta) return;
    if (contagem) contagem.dataset.pronta = "1";
    var filtros = Array.prototype.slice.call(raiz.querySelectorAll(".magia-filtro"));

    function aplicarFiltros() {
      var termo = normalizar(busca ? busca.value : "");
      var visiveis = 0, total = 0;
      tabelas.forEach(function (tabela) {
        var corpo = tabela.tBodies[0];
        var linhas = Array.prototype.slice.call(corpo.rows);
        var ativa = dentroDeAbaAtiva(tabela);
        linhas.forEach(function (linha) {
          var ok = !termo || normalizar(linha.textContent).indexOf(termo) !== -1;
          filtros.forEach(function (sel) {
            if (!ok || !sel.value) return;
            var indice = indiceColunaMagia(tabela, sel.dataset.coluna);
            if (indice === -1) return;
            var valorCelula = normalizar(textoCelula(linha, indice));
            var valorFiltro = normalizar(sel.value);
            var bate = sel.dataset.modo === "contem"
              ? valorCelula.indexOf(valorFiltro) !== -1
              : valorCelula === valorFiltro;
            if (!bate) ok = false;
          });
          linha.hidden = !ok;
          if (ativa) { total++; if (ok) visiveis++; }
        });
      });
      if (contagem) {
        contagem.textContent = visiveis === total ? total + " magias" : visiveis + " de " + total + " magias";
      }
    }

    if (busca) busca.addEventListener("input", aplicarFiltros);
    filtros.forEach(function (sel) { sel.addEventListener("change", aplicarFiltros); });
    document.querySelectorAll(".tabbed-set > input").forEach(function (entrada) {
      entrada.addEventListener("change", aplicarFiltros);
    });
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

  // Sobe pelos .tabbed-set ancestrais de `elemento` (podem ser vários, se as abas estiverem
  // aninhadas) e devolve false se algum deles estiver numa aba diferente da selecionada.
  function dentroDeAbaAtiva(elemento) {
    var bloco = elemento.closest(".tabbed-block");
    while (bloco) {
      var conjunto = bloco.closest(".tabbed-set");
      if (!conjunto) return true;
      var indice = Array.prototype.indexOf.call(bloco.parentElement.children, bloco);
      var entrada = conjunto.querySelectorAll(":scope > input")[indice];
      if (entrada && !entrada.checked) return false;
      bloco = conjunto.closest(".tabbed-block");
    }
    return true;
  }

  function filtrarIndicePorAba() {
    document.querySelectorAll(".md-sidebar--secondary .md-nav__item").forEach(function (item) {
      var link = item.querySelector(":scope > .md-nav__link[href^='#']");
      if (!link) return;
      var alvo = document.getElementById(decodeURIComponent(link.getAttribute("href").slice(1)));
      // Sem elemento correspondente (não devia acontecer) deixa visível, por segurança.
      item.style.display = alvo && !dentroDeAbaAtiva(alvo) ? "none" : "";
    });
  }

  function iniciar() {
    montarTabelaNpcs(document);
    montarPainelMagias(document);
    abrirAbaDaAncora();
    filtrarIndicePorAba();
    document.querySelectorAll(".tabbed-set > input").forEach(function (entrada) {
      entrada.addEventListener("change", filtrarIndicePorAba);
    });
  }

  // Compatível com a navegação instantânea do Material (document$), se for ativada um dia.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(iniciar);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
  window.addEventListener("hashchange", function () {
    abrirAbaDaAncora();
    filtrarIndicePorAba();
  });
})();
