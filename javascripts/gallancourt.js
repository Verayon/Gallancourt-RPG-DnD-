/* Comportamentos da wiki de Gallancourt.
 *
 * 1. Tabelas filtráveis de NPCs/Lugares/Jogadores: ordenar clicando no cabeçalho, filtrar por
 *    coluna (listas no cabeçalho) e filtrar por texto livre — mesma lógica (prepararTabelaFiltravel)
 *    reaproveitada pelas três.
 * 2. Páginas com abas: um link para uma seção (#ancora) abre a aba que a contém.
 * 3. Índice (TOC) da página: só mostra os cabeçalhos da aba selecionada no momento — clicar num
 *    cabeçalho de outra aba, escondido, não rolava a página (a aba continuava fechada).
 * 4. Magias (magias/index.md e magias/por-classe/*.md): mesma ideia das tabelas acima, mas com
 *    uma barra de filtros fixa (fora das abas) controlando várias tabelas ao mesmo tempo — uma
 *    por aba de nível — e colunas de classificação (Ritual, Categoria, Tipo de Dano…) escondidas
 *    por CSS, usadas só pelos filtros, não pela ordenação por clique.
 * 5. Formulários embutidos de "Adicionar NPC/Lugar/Jogador" (personagens/lugares/jogadores
 *    index.md): falam com a API JSON do Painel (admin/app.py, /api/npcs|lugares|jogadores) via
 *    docs/javascripts/painel-fetch.js, sem redirecionar para outra aba.
 * 6. Tabelas de Roadmap e Bugs: mesma prepararTabelaFiltravel de novo.
 * 7. Menu da esquerda: ao abrir uma categoria de topo, as outras que estiverem abertas retraem
 *    (restringirAccordionNav) — só uma por vez.
 */
(function () {
  "use strict";

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

  // Tabela filtrável genérica, usada pelas tabelas de NPCs, Lugares e Jogadores.
  // opcoes: { tabela, busca, contagem, colunasComFiltro, colunasSemOrdem, rotuloPlural }
  function prepararTabelaFiltravel(opcoes) {
    var tabela = opcoes.tabela;
    if (!tabela || tabela.dataset.pronta) return;
    tabela.dataset.pronta = "1";

    var corpo = tabela.tBodies[0];
    var linhas = Array.prototype.slice.call(corpo.rows);
    var cabecalhos = Array.prototype.slice.call(tabela.tHead.rows[0].cells);
    var busca = opcoes.busca;
    var contagem = opcoes.contagem;
    var colunasComFiltro = opcoes.colunasComFiltro || [];
    var colunasSemOrdem = opcoes.colunasSemOrdem || [];
    var rotuloPlural = opcoes.rotuloPlural || "itens";
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
          ? linhas.length + " " + rotuloPlural
          : visiveis + " de " + linhas.length + " " + rotuloPlural;
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

      if (colunasSemOrdem.indexOf(rotulo) === -1) {
        var botao = document.createElement("button");
        botao.type = "button";
        botao.className = "tabela-ordenar";
        botao.textContent = rotulo;
        botao.title = "Ordenar por " + rotulo;
        botao.addEventListener("click", function () { ordenar(indice); });
        th.appendChild(botao);
        th.setAttribute("aria-sort", "none");
      } else {
        var span = document.createElement("span");
        span.className = "tabela-rotulo";
        span.textContent = rotulo;
        th.appendChild(span);
      }

      if (colunasComFiltro.indexOf(rotulo) !== -1) {
        var valores = {};
        linhas.forEach(function (linha) { valores[textoCelula(linha, indice)] = true; });
        var lista = document.createElement("select");
        lista.className = "tabela-filtro";
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

  function montarTabelaNpcs(raiz) {
    prepararTabelaFiltravel({
      tabela: raiz.querySelector(".npc-tabela table"),
      busca: raiz.querySelector(".npc-busca"),
      contagem: raiz.querySelector(".npc-contagem"),
      colunasComFiltro: ["Título", "Raça", "Cidade", "Afiliação", "Situação"],
      colunasSemOrdem: ["Retrato"],
      rotuloPlural: "NPCs",
    });
  }

  function montarTabelaLugares(raiz) {
    prepararTabelaFiltravel({
      tabela: raiz.querySelector(".lugar-tabela table"),
      busca: raiz.querySelector(".lugar-busca"),
      contagem: raiz.querySelector(".lugar-contagem"),
      colunasComFiltro: ["Situado", "Região", "Reino"],
      rotuloPlural: "lugares",
    });
  }

  function montarTabelaJogadores(raiz) {
    prepararTabelaFiltravel({
      tabela: raiz.querySelector(".jogador-tabela table"),
      busca: raiz.querySelector(".jogador-busca"),
      contagem: raiz.querySelector(".jogador-contagem"),
      colunasComFiltro: ["Jogador", "Classe"],
      rotuloPlural: "jogadores",
    });
  }

  function montarTabelaDotes(raiz) {
    prepararTabelaFiltravel({
      tabela: raiz.querySelector(".dote-tabela table"),
      busca: raiz.querySelector(".dote-busca"),
      contagem: raiz.querySelector(".dote-contagem"),
      colunasComFiltro: ["Pré-requisito", "Fonte"],
      rotuloPlural: "dotes",
    });
  }

  function montarTabelaPericias(raiz) {
    prepararTabelaFiltravel({
      tabela: raiz.querySelector(".pericia-tabela table"),
      busca: raiz.querySelector(".pericia-busca"),
      contagem: raiz.querySelector(".pericia-contagem"),
      colunasComFiltro: ["Atributo", "Fonte"],
      rotuloPlural: "perícias",
    });
  }

  function montarTabelaRoadmap(raiz) {
    prepararTabelaFiltravel({
      tabela: raiz.querySelector(".roadmap-tabela table"),
      busca: raiz.querySelector(".roadmap-busca"),
      contagem: raiz.querySelector(".roadmap-contagem"),
      colunasComFiltro: ["Prioridade", "Funcionalidade", "Status"],
      rotuloPlural: "itens",
    });
  }

  function montarTabelaBugs(raiz) {
    prepararTabelaFiltravel({
      tabela: raiz.querySelector(".bug-tabela table"),
      busca: raiz.querySelector(".bug-busca"),
      contagem: raiz.querySelector(".bug-contagem"),
      colunasComFiltro: ["Área", "Status"],
      rotuloPlural: "bugs",
    });
  }

  function montarTabelaMonstros(raiz) {
    prepararTabelaFiltravel({
      tabela: raiz.querySelector(".monstro-tabela table"),
      busca: raiz.querySelector(".monstro-busca"),
      contagem: raiz.querySelector(".monstro-contagem"),
      colunasComFiltro: ["Tamanho", "Tipo", "Alinhamento"],
      rotuloPlural: "monstros",
    });
  }

  // Itens (docs/itens/index.md): uma aba por categoria, cada uma com sua própria
  // busca+contagem+tabela (as colunas mudam por categoria) — por isso, ao contrário das outras
  // tabelas, itera cada aba (.tabbed-block) em vez de pegar só a primeira busca/tabela da página.
  function montarTabelaItens(raiz) {
    raiz.querySelectorAll(".tabbed-block .item-tabela").forEach(function (bloco) {
      var tabela = bloco.querySelector("table");
      var aba = bloco.closest(".tabbed-block");
      if (!tabela || !aba) return;
      var cabecalhos = Array.prototype.map.call(tabela.tHead.rows[0].cells, function (th) {
        return th.textContent.trim();
      });
      prepararTabelaFiltravel({
        tabela: tabela,
        busca: aba.querySelector(".item-busca"),
        contagem: aba.querySelector(".item-contagem"),
        colunasComFiltro: cabecalhos.filter(function (c) { return c !== "Nome"; }),
        rotuloPlural: "itens",
      });
    });
  }

  // Menu da esquerda: só uma categoria de topo aberta por vez. O Material usa um <input
  // type=checkbox> por item de menu com subcategorias (ver md-nav__toggle); ao marcar um,
  // desmarca os outros checkboxes do mesmo nível (irmãos na mesma <ul>) — funciona em qualquer
  // profundidade, mas na prática só os de topo (Lore, Wiki, Compêndio...) têm vários irmãos.
  function restringirAccordionNav() {
    document.querySelectorAll(".md-nav--primary input.md-nav__toggle").forEach(function (toggle) {
      if (toggle.dataset.accordionPronto) return;
      toggle.dataset.accordionPronto = "1";
      toggle.addEventListener("change", function () {
        if (!toggle.checked) return;
        var item = toggle.closest(".md-nav__item");
        var lista = item && item.parentElement;
        if (!lista) return;
        Array.prototype.slice.call(lista.children).forEach(function (irmao) {
          if (irmao === item) return;
          var outro = irmao.querySelector(":scope > input.md-nav__toggle");
          if (outro && outro.checked) outro.checked = false;
        });
      });
    });
  }

  // Formulários embutidos "Adicionar NPC/Lugar/Jogador" — ver docs/javascripts/painel-fetch.js.
  var CONFIG_ENTIDADE = {
    npc: {
      endpoint: "/api/npcs", rotuloBotao: "Criar NPC", descricao: true, imagem: true, generico: true,
      campos: [
        ["nome", "Nome", true], ["titulo", "Título (ex.: Marquesa, Capitão, Mestre)", false],
        ["raca", "Raça", false], ["cidade", "Cidade", false],
        ["afiliacao", "Afiliação (casa, facção, organização)", false],
        ["resumo", "Resumo de uma linha (aparece na tabela)", false],
      ],
    },
    lugar: {
      endpoint: "/api/lugares", rotuloBotao: "Criar lugar", descricao: true,
      campos: [
        ["nome", "Nome", true],
        ["situado", "Situado em (cidade onde fica — ou \"Cidade\"/\"Vila\" se este lugar for um assentamento)", false],
        ["regiao", "Região (ex.: Costa norte, Fronteira leste)", false],
        ["reino", "Reino ou estado (ex.: Gallancourt, L'Ordre de Célestien)", false],
        ["resumo", "Descrição de uma linha (aparece na lista)", false],
      ],
    },
    jogador: {
      endpoint: "/api/jogadores", rotuloBotao: "Criar jogador",
      campos: [
        ["nome", "Nome do personagem", true], ["jogador", "Nome de quem joga", false],
        ["raca_classe", "Raça e classe (ex.: Elfo guerreiro)", false],
        ["resumo", "Resumo de uma linha (aparece na lista)", false],
      ],
    },
  };

  function montarFormularioEntidade(elemento) {
    if (elemento.dataset.pronta) return;
    elemento.dataset.pronta = "1";
    var P = window.GallancourtPainel;
    var cfg = CONFIG_ENTIDADE[elemento.getAttribute("data-tipo")];
    if (!cfg || !P) return;
    var baseUrl = P.base(elemento);

    var html = '<form class="entidade-formulario__form">';
    cfg.campos.forEach(function (c) {
      html += "<label>" + P.escapeHtml(c[1]) + '<input type="text" name="' + c[0] + '"'
        + (c[2] ? " required" : "") + "></label>";
    });
    if (cfg.descricao) {
      html += '<label>Descrição<textarea name="descricao" rows="4" '
        + 'placeholder="Quem é, como age, o que quer / como é, onde fica, o que acontece ali…"></textarea></label>';
    }
    if (cfg.imagem) {
      html += '<label>Retrato (opcional)<input type="file" name="imagem" accept="image/*"></label>';
    }
    if (cfg.generico) {
      html += '<label class="check"><input type="checkbox" name="generico"> '
        + "É um NPC genérico (modelo reutilizável — guarda, camponês, nobre… — não alguém específico)</label>";
    }
    html += '<button type="submit" class="botao-principal">' + P.escapeHtml(cfg.rotuloBotao) + "</button>"
      + '<p class="entidade-formulario__resultado" aria-live="polite"></p></form>';
    elemento.innerHTML = html;

    var form = elemento.querySelector("form");
    var resultado = elemento.querySelector(".entidade-formulario__resultado");
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      resultado.className = "entidade-formulario__resultado";
      resultado.textContent = "Criando…";
      P.chamarFormData(baseUrl, cfg.endpoint, new FormData(form)).then(function (r) {
        resultado.className = "entidade-formulario__resultado entidade-formulario__resultado--ok";
        resultado.textContent = "✅ Criado: " + r.arquivo + ". Recarregue a página para ver na tabela.";
        form.reset();
      }).catch(function (erro) {
        resultado.className = "entidade-formulario__resultado entidade-formulario__resultado--erro";
        resultado.textContent = "⚠️ " + erro.message;
      });
    });
  }

  function montarFormulariosEntidade(raiz) {
    Array.prototype.slice.call(raiz.querySelectorAll(".criar-entidade")).forEach(montarFormularioEntidade);
  }

  // Colunas da tabela de magias que ficam escondidas por CSS (nth-last-child(-n+5) — ver
  // extra.css) e por isso não recebem botão de ordenação, só servem de alvo para os filtros da
  // barra. São sempre as últimas 5, independente de quantas colunas visíveis vêm antes.
  var COLUNAS_MAGIA_SEM_ORDEM = [
    "Ritual", "Concentração", "Categoria", "Tipo de Dano", "Tipo de Alcance",
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

  // Exposta para docs/javascripts/criar-sessao.js reaproveitar a mesma tabela filtrável (com
  // checkboxes de seleção) nas três listas de NPCs/Jogadores/Lugares do criador de sessão.
  window.GallancourtTabelas = { prepararTabelaFiltravel: prepararTabelaFiltravel };

  function iniciar() {
    montarTabelaNpcs(document);
    montarTabelaLugares(document);
    montarTabelaJogadores(document);
    montarTabelaDotes(document);
    montarTabelaPericias(document);
    montarTabelaRoadmap(document);
    montarTabelaBugs(document);
    montarTabelaMonstros(document);
    montarTabelaItens(document);
    montarFormulariosEntidade(document);
    montarPainelMagias(document);
    restringirAccordionNav();
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
