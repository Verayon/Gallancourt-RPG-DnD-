/* Criador de sessão embutido (Mestre → Sessões): busca os NPCs/Jogadores/Lugares já cadastrados
 * via API JSON do Painel (admin/app.py, /api/npcs|jogadores|lugares|sessoes/*), deixa escolher
 * quais participam da sessão em tabelas filtráveis com checkbox, e manda tudo (mais um prompt de
 * texto livre, salvo como anotação — sem IA nesta versão) para /api/sessoes/nova.
 *
 * Reaproveita docs/javascripts/painel-fetch.js (fetch/erro) e a tabela filtrável genérica de
 * docs/javascripts/gallancourt.js (window.GallancourtTabelas), construindo o <table> a partir do
 * JSON recebido em vez de ler um já renderizado no HTML da página.
 */
(function () {
  "use strict";

  var COLUNAS_NPC = [{ rotulo: "Título", chave: "titulo" }, { rotulo: "Raça", chave: "raca" },
    { rotulo: "Cidade", chave: "cidade" }, { rotulo: "Afiliação", chave: "afiliacao" }];
  var COLUNAS_JOGADOR = [{ rotulo: "Jogador", chave: "jogador" }, { rotulo: "Raça e classe", chave: "raca_classe" }];
  var COLUNAS_LUGAR = [{ rotulo: "Tipo", chave: "tipo" }, { rotulo: "Cidade", chave: "cidade" }];

  var CAMPOS_BASICOS = [
    ["data", "Data"], ["resumo_breve", "Resumo breve (aparece no card da lista)"],
    ["nivel", "Nível sugerido"], ["duracao", "Duração estimada"], ["tom", "Tom"],
    ["missao", "Missão oferecida"], ["recompensa", "Recompensa"],
  ];

  function montarTabelaSelecao(P, T, container, classe, grupo, colunas, linhas, rotuloPlural) {
    if (!linhas.length) {
      container.innerHTML = "<p><em>Nenhum cadastrado ainda.</em></p>";
      return;
    }
    var thead = "<tr><th></th>" + colunas.map(function (c) {
      return "<th>" + P.escapeHtml(c.rotulo) + "</th>";
    }).join("") + "<th>Resumo</th></tr>";
    var corpo = linhas.map(function (item) {
      return "<tr><td><input type=\"checkbox\" class=\"criar-sessao__check\" data-grupo=\"" + grupo
        + "\" value=\"" + P.escapeHtml(item.rel_docs) + "\"></td>"
        + colunas.map(function (c) { return "<td>" + P.escapeHtml(item[c.chave] || "—") + "</td>"; }).join("")
        + "<td>" + P.escapeHtml(item.resumo || "—") + "</td></tr>";
    }).join("");
    container.innerHTML =
      '<div class="' + classe + '-ferramentas"><p>'
      + '<input type="search" class="' + classe + '-busca" placeholder="Filtrar…" aria-label="Filtrar">'
      + '<span class="' + classe + '-contagem" aria-live="polite"></span>'
      + "</p></div>"
      + '<div class="' + classe + '-tabela"><table><thead>' + thead + "</thead><tbody>" + corpo + "</tbody></table></div>";
    T.prepararTabelaFiltravel({
      tabela: container.querySelector("." + classe + "-tabela table"),
      busca: container.querySelector("." + classe + "-busca"),
      contagem: container.querySelector("." + classe + "-contagem"),
      colunasComFiltro: colunas.map(function (c) { return c.rotulo; }),
      colunasSemOrdem: [""],
      rotuloPlural: rotuloPlural,
    });
  }

  function renderizarFormulario(raiz, P, T, base, dados) {
    var html = '<form class="criar-sessao__form">';
    html += '<div class="criar-sessao__basicos">';
    html += '<label>Número<input type="number" name="numero" value="' + dados.numero + '" min="0" required></label>';
    html += '<label>Título<input type="text" name="titulo" placeholder="Ex.: O Posto Cinzento" required></label>';
    CAMPOS_BASICOS.forEach(function (c) {
      html += "<label>" + P.escapeHtml(c[1]) + '<input type="text" name="' + c[0] + '"></label>';
    });
    html += "</div>";
    html += '<label>Resumo rápido (texto da sessão)<textarea name="resumo" rows="4" '
      + 'placeholder="Em poucas linhas: o que acontece nesta sessão."></textarea></label>';

    html += "<h3>NPCs</h3><div class=\"criar-sessao__secao\" data-secao=\"npc\"></div>";
    if (dados.npcsGenericos.length) {
      html += "<h4>NPCs genéricos (modelos reutilizáveis)</h4><div class=\"criar-sessao__secao\" data-secao=\"npc-generico\"></div>";
    }
    html += "<h3>Jogadores</h3><div class=\"criar-sessao__secao\" data-secao=\"jogador\"></div>";
    html += "<h3>Lugares</h3><div class=\"criar-sessao__secao\" data-secao=\"lugar\"></div>";

    html += '<label>Como você quer que esta sessão seja organizada'
      + '<textarea name="prompt" rows="5" placeholder="Descreva o que você imagina para esta sessão — vira uma anotação na aba Resumo (ainda não há geração automática por IA)."></textarea></label>';
    html += '<p class="criar-sessao__aviso">O texto acima só é salvo como anotação sua — nenhuma IA é chamada nesta versão.</p>';
    html += '<button type="submit" class="botao-principal">Criar sessão</button>';
    html += '<p class="criar-sessao__resultado" aria-live="polite"></p>';
    html += "</form>";
    raiz.innerHTML = html;

    montarTabelaSelecao(P, T, raiz.querySelector('[data-secao="npc"]'), "npc", "npc", COLUNAS_NPC, dados.npcs, "NPCs");
    if (dados.npcsGenericos.length) {
      montarTabelaSelecao(
        P, T, raiz.querySelector('[data-secao="npc-generico"]'), "npc", "npc", COLUNAS_NPC.slice(0, 2),
        dados.npcsGenericos, "NPCs genéricos",
      );
    }
    montarTabelaSelecao(P, T, raiz.querySelector('[data-secao="jogador"]'), "jogador", "jogador", COLUNAS_JOGADOR, dados.jogadores, "jogadores");
    montarTabelaSelecao(P, T, raiz.querySelector('[data-secao="lugar"]'), "lugar", "lugar", COLUNAS_LUGAR, dados.lugares, "lugares");

    var form = raiz.querySelector("form");
    var resultado = raiz.querySelector(".criar-sessao__resultado");
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      resultado.className = "criar-sessao__resultado";
      resultado.textContent = "Criando…";

      var fd = new FormData(form);
      var campos = {};
      CAMPOS_BASICOS.forEach(function (c) { campos[c[0]] = fd.get(c[0]) || ""; });

      function marcados(grupo) {
        return Array.prototype.slice.call(
          raiz.querySelectorAll('.criar-sessao__check[data-grupo="' + grupo + '"]:checked'),
        ).map(function (c) { return c.value; });
      }

      var corpo = {
        numero: fd.get("numero"), titulo: fd.get("titulo"), resumo: fd.get("resumo"),
        campos: campos, prompt: fd.get("prompt"),
        npcs: marcados("npc"), jogadores: marcados("jogador"), lugares: marcados("lugar"),
      };

      P.chamarJSON(base, "/api/sessoes/nova", "POST", corpo).then(function (r) {
        resultado.className = "criar-sessao__resultado criar-sessao__resultado--ok";
        resultado.innerHTML = "✅ Sessão criada: <a href=\"../../" + P.escapeHtml(r.rel_docs.replace(/\.md$/, "/"))
          + "\">abrir a página</a>.";
        form.reset();
      }).catch(function (erro) {
        resultado.className = "criar-sessao__resultado criar-sessao__resultado--erro";
        resultado.textContent = "⚠️ " + erro.message;
      });
    });
  }

  function montarCriadorSessao(raiz) {
    if (raiz.dataset.pronta) return;
    raiz.dataset.pronta = "1";
    var P = window.GallancourtPainel;
    var T = window.GallancourtTabelas;
    if (!P || !T) return;
    var base = P.base(raiz);

    raiz.innerHTML = '<p class="criar-sessao__carregando">Carregando NPCs, jogadores e lugares já cadastrados…</p>';
    Promise.all([
      P.chamarJSON(base, "/api/sessoes/proxima-numero"),
      P.chamarJSON(base, "/api/npcs"),
      P.chamarJSON(base, "/api/npcs/genericos"),
      P.chamarJSON(base, "/api/jogadores"),
      P.chamarJSON(base, "/api/lugares"),
    ]).then(function (resultados) {
      renderizarFormulario(raiz, P, T, base, {
        numero: resultados[0].numero, npcs: resultados[1].itens, npcsGenericos: resultados[2].itens,
        jogadores: resultados[3].itens, lugares: resultados[4].itens,
      });
    }).catch(function (erro) {
      raiz.innerHTML = P.erroHtml(base, erro);
    });
  }

  function iniciar() {
    Array.prototype.slice.call(document.querySelectorAll(".criar-sessao")).forEach(montarCriadorSessao);
  }

  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(iniciar);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
