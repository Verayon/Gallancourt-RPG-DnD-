/* Painel de Iniciativa embutido — widget que roda dentro da própria aba "Painel de Iniciativa"
 * de uma página de sessão, falando por fetch() com a API JSON do Painel do Mestre local
 * (admin/app.py, rotas /api/sessao-ao-vivo/...). Sem iframe, sem recarregar a página: toda ação
 * manda uma chamada e redesenha o widget a partir da resposta.
 *
 * Mesma lógica de negócio do Painel (admin/sessao_viva.py) — este arquivo só desenha e dispara
 * chamadas, nunca decide sozinho ordem de turno, dano, etc.
 */
(function () {
  "use strict";

  function escapeHtml(valor) {
    return String(valor == null ? "" : valor)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function modificador(valor) {
    var n = parseInt(valor, 10);
    if (isNaN(n)) return "+0";
    var mod = Math.floor((n - 10) / 2);
    return mod >= 0 ? "+" + mod : String(mod);
  }

  function linhasParaTrechos(texto) {
    return (texto || "").split("\n").map(function (l) { return l.trim(); }).filter(Boolean).map(function (linha) {
      var i = linha.indexOf(":");
      if (i === -1) return { nome: "", desc: linha };
      return { nome: linha.slice(0, i).trim(), desc: linha.slice(i + 1).trim() };
    });
  }

  function comboFicha(f) {
    return f.pagina_rel_docs + "::" + f.slug;
  }

  function Widget(raiz) {
    this.raiz = raiz;
    this.pagina = raiz.getAttribute("data-pagina");
    // Site e Painel são a mesma origem/porta (ver admin/app.py) — caminho relativo, sem CORS.
    this.base = "";
    this.dados = null;
    this.raiz.classList.add("painel-iniciativa--pronto");
    this.ligarEventos();
    this.chamar("GET", "");
  }

  Widget.prototype.url = function (caminho) {
    return this.base + "/api/sessao-ao-vivo/" + this.pagina + (caminho || "");
  };

  Widget.prototype.chamar = function (metodo, caminho, corpo) {
    var self = this;
    var opcoes = { method: metodo };
    if (corpo !== undefined) {
      opcoes.headers = { "Content-Type": "application/json" };
      opcoes.body = JSON.stringify(corpo);
    }
    return fetch(this.url(caminho), opcoes)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (dados) {
        if (dados.erro) throw new Error(dados.erro);
        self.dados = dados;
        self.renderizar();
      })
      .catch(function (erro) {
        self.renderizarErro(erro);
      });
  };

  Widget.prototype.renderizarErro = function (erro) {
    this.raiz.innerHTML =
      '<p class="painel-iniciativa__erro">⚠️ Não consegui falar com o Painel do Mestre. ' +
      "Confirme que ele está rodando (<code>admin\\iniciar-painel.bat</code>) e recarregue a " +
      "página. <small>(" + escapeHtml(erro && erro.message) + ")</small></p>";
  };

  // --------------------------------------------------------------------
  // Montagem do HTML — cada seção devolve uma string; renderizar() junta tudo.
  // --------------------------------------------------------------------

  Widget.prototype.renderizar = function () {
    this.raiz.innerHTML =
      this._secaoNotas() + this._secaoIniciativa() + this._secaoAcoes() + this._secaoPerigo();
  };

  Widget.prototype._secaoNotas = function () {
    var d = this.dados;
    var notas = (d.estado.notas || []).map(function (n, i) {
      return (
        '<li><span class="pi-nota-hora">' + escapeHtml(n.hora) + "</span> " + escapeHtml(n.texto) +
        ' <button type="button" class="botao-remover" data-acao="remover-nota" data-indice="' + i +
        '" title="Remover">×</button></li>'
      );
    }).join("");

    return (
      '<section class="pi-secao" id="pi-notas"><h3>Notas e resumo</h3>' +
      '<form class="pi-form-inline" data-acao="adicionar-nota">' +
      '<input type="text" name="texto" placeholder="Anotação rápida (fica com a hora marcada)…">' +
      '<button type="submit" class="botao-secundario">Adicionar</button></form>' +
      (notas ? '<ul class="pi-lista-notas">' + notas + "</ul>" : '<p class="ajuda">Nenhuma anotação ainda.</p>') +
      '<form data-acao="salvar-resumo"><label>Resumo da sessão (vira o resumo ao registrar no Diário)' +
      '<textarea name="resumo" rows="4" placeholder="Vá escrevendo o resumo conforme a sessão acontece…">' +
      escapeHtml(d.estado.resumo) + "</textarea></label>" +
      '<button type="submit" class="botao-principal">Salvar resumo</button></form></section>'
    );
  };

  Widget.prototype._fichaDaVezHtml = function () {
    var f = this.dados.ficha_da_vez;
    if (!f) return "";
    var atributos = this.dados.atributos_ficha.map(function (a) {
      var r = this.dados.rotulos_atributos[a];
      var v = f[a] || "—";
      return "<span><strong>" + escapeHtml(r) + "</strong> " + escapeHtml(v) + " (" + modificador(v) + ")</span>";
    }, this).join(" ");
    var acoes = "";
    if (f.acoes) {
      acoes = "<p><strong>Ações</strong></p><ul>" + linhasParaTrechos(f.acoes).map(function (t) {
        return "<li>" + (t.nome ? "<strong>" + escapeHtml(t.nome) + ".</strong> " : "") + escapeHtml(t.desc) + "</li>";
      }).join("") + "</ul>";
    }
    return (
      '<div class="pi-ficha-da-vez"><h4>' + escapeHtml(f.nome) + ' <span class="ajuda">— ficha de combate</span></h4>' +
      (f.subtitulo ? '<p class="ajuda">' + escapeHtml(f.subtitulo) + "</p>" : "") +
      '<div class="stat-block__chips"><span><strong>CA</strong> ' + escapeHtml(f.ca) +
      "</span><span><strong>PV</strong> " + escapeHtml(f.pv) + "</span><span><strong>Deslocamento</strong> " +
      escapeHtml(f.deslocamento) + "</span></div>" +
      '<div class="pi-ficha-da-vez__atributos">' + atributos + "</div>" +
      (f.equipamento ? "<p><strong>Equipamento</strong> " + escapeHtml(f.equipamento) + "</p>" : "") +
      acoes + "</div>"
    );
  };

  Widget.prototype._secaoIniciativa = function () {
    var d = this.dados;
    var self = this;

    var opcoesFicha = '<option value="">— nenhuma / preencher na mão —</option>' +
      d.fichas_disponiveis.map(function (f) {
        return '<option value="' + escapeHtml(comboFicha(f)) + '">' + escapeHtml(f.nome) +
          " (" + escapeHtml(f.pagina_titulo) + ")</option>";
      }).join("");

    var formAdicionar =
      '<form class="pi-form-combatente" data-acao="adicionar-combatente">' +
      '<label>Nome<input type="text" name="nome"></label>' +
      '<label>Tipo<select name="tipo"><option value="jogador">Jogador</option>' +
      '<option value="npc" selected>NPC</option></select></label>' +
      '<label>Ficha vinculada <span class="opcional">(opcional)</span><select name="ficha">' +
      opcoesFicha + "</select></label>" +
      '<label>Iniciativa<input type="number" name="iniciativa" required></label>' +
      '<label>PV atual <span class="opcional">(vem da ficha, se vinculada)</span>' +
      '<input type="number" name="pv_atual" min="0"></label>' +
      '<label>PV máximo <span class="opcional">(vem da ficha, se vinculada)</span>' +
      '<input type="number" name="pv_maximo" min="0"></label>' +
      '<button type="submit" class="botao-secundario">Adicionar à iniciativa</button></form>' +
      '<p class="ajuda">Escolher uma ficha preenche o nome e o PV sozinho (se deixados em branco) ' +
      "e faz a ficha completa aparecer quando for a vez desse NPC.</p>";

    if (!d.combatentes.length) {
      return (
        '<section class="pi-secao" id="pi-iniciativa"><h3>Iniciativa</h3>' + formAdicionar +
        '<p class="ajuda">Ninguém na iniciativa ainda — adicione os combatentes acima.</p></section>'
      );
    }

    var turno = d.estado.turno_atual === null
      ? '<span class="ajuda">— combate ainda não começou</span>'
      : "— turno de <strong>" + escapeHtml(d.combatentes[0].nome) + "</strong>";

    var linhas = d.combatentes.map(function (c) {
      var classes = ["pi-combatente"];
      if (c.id === d.estado.turno_atual) classes.push("pi-combatente--atual");
      if (c.caido) classes.push("pi-combatente--caido");
      if (c.morto) classes.push("pi-combatente--morto");
      var etiqueta = c.morto ? '<span class="etiqueta etiqueta--morto">morto</span>'
        : c.caido ? '<span class="etiqueta etiqueta--caido">caído</span>' : "";
      var pv = c.pv_atual != null ? c.pv_atual + (c.pv_maximo ? "/" + c.pv_maximo : "") : "—";
      return (
        '<tr class="' + classes.join(" ") + '" data-cid="' + c.id + '">' +
        "<td>" + c.iniciativa + "</td>" +
        "<td>" + escapeHtml(c.nome) + " " + etiqueta + "</td>" +
        "<td>" + (c.tipo === "jogador" ? "Jogador" : "NPC") + "</td>" +
        '<td>' + pv + ' <form class="pi-form-inline" data-acao="ajustar-pv" data-cid="' + c.id + '">' +
        '<input type="number" name="delta" placeholder="±PV" class="input-pequeno">' +
        '<button type="submit" class="botao-remover" title="Aplicar ao PV">OK</button></form></td>' +
        '<td><form class="pi-form-inline" data-acao="atualizar-status" data-cid="' + c.id + '">' +
        '<input type="text" name="status" value="' + escapeHtml((c.status || []).join(", ")) +
        '" class="input-medio" placeholder="exausto, envenenado…">' +
        '<button type="submit" class="botao-remover" title="Atualizar status">OK</button></form></td>' +
        '<td class="col-acoes-combatente">' +
        '<button type="button" class="botao-remover" data-acao="flag-caido" data-cid="' + c.id + '">' +
        (c.caido ? "Reerguer" : "Caído") + "</button> " +
        '<button type="button" class="botao-remover" data-acao="flag-morto" data-cid="' + c.id + '">' +
        (c.morto ? "Reviver" : "Morto") + "</button> " +
        '<button type="button" class="botao-remover" data-acao="remover-combatente" data-cid="' + c.id + '">' +
        "Remover</button></td></tr>"
      );
    }).join("");

    return (
      '<section class="pi-secao" id="pi-iniciativa"><h3>Iniciativa</h3>' + formAdicionar +
      '<div class="pi-turno-atual"><strong>Rodada ' + d.estado.rodada + "</strong> " + turno +
      '<form class="pi-form-inline" data-acao="proximo-turno">' +
      '<button type="submit" class="botao-principal">Próximo turno →</button></form></div>' +
      this._fichaDaVezHtml() +
      '<table class="tabela-combate"><thead><tr><th>Iniciativa</th><th>Nome</th><th>Tipo</th>' +
      "<th>PV</th><th>Status</th><th></th></tr></thead><tbody>" + linhas + "</tbody></table>" +
      '<p class="ajuda">A lista sempre começa por quem está na vez.</p></section>'
    );
  };

  Widget.prototype._secaoAcoes = function () {
    var d = this.dados;
    if (!d.combatentes.length) {
      return (
        '<section class="pi-secao" id="pi-acoes"><h3>Ações (ataque, cura…)</h3>' +
        '<p class="ajuda">Adicione combatentes na iniciativa para poder registrar ações.</p></section>'
      );
    }

    var opcoesAutor = d.combatentes.map(function (c) {
      return '<option value="' + c.id + '"' + (c.id === d.estado.turno_atual ? " selected" : "") + ">" +
        escapeHtml(c.nome) + "</option>";
    }).join("");
    var opcoesAlvo = '<option value="">—</option>' + d.combatentes.map(function (c) {
      return '<option value="' + c.id + '">' + escapeHtml(c.nome) + "</option>";
    }).join("");

    var form =
      '<form class="pi-form-acao" data-acao="registrar-acao">' +
      '<label>Quem agiu<select name="autor_id">' + opcoesAutor + "</select></label>" +
      '<label>Tipo<select name="tipo"><option value="ataque">Ataque</option>' +
      '<option value="cura">Cura</option><option value="outro">Outro</option></select></label>' +
      '<label>Em quem <span class="opcional">(opcional)</span><select name="alvo_id">' +
      opcoesAlvo + "</select></label>" +
      '<label>Arma, magia ou habilidade <span class="opcional">(opcional)</span>' +
      '<input type="text" name="meio" placeholder="ex.: Cimitarra, Bola de Fogo…"></label>' +
      '<label>Valor <span class="opcional">(dano ou cura)</span><input type="number" name="valor" min="0"></label>' +
      '<label>Observação <span class="opcional">(opcional)</span><input type="text" name="obs"></label>' +
      '<button type="submit" class="botao-secundario">Registrar ação</button></form>';

    if (!d.estado.log_acoes.length) {
      return (
        '<section class="pi-secao" id="pi-acoes"><h3>Ações (ataque, cura…)</h3>' + form +
        '<p class="ajuda">Nenhuma ação registrada ainda.</p></section>'
      );
    }

    var rotulos = d.rotulos_acao;
    var linhasLog = d.estado.log_acoes.slice().reverse().map(function (a) {
      return (
        "<tr><td>" + a.rodada + "</td><td>" + escapeHtml(a.autor_nome) + "</td><td>" + rotulos[a.tipo] +
        "</td><td>" + escapeHtml(a.meio || "—") + "</td><td>" + escapeHtml(a.alvo_nome || "—") + "</td><td>" +
        (a.valor != null ? a.valor : "—") + "</td><td>" + escapeHtml(a.obs) + "</td>" +
        '<td><button type="button" class="botao-remover" data-acao="remover-acao" data-id="' + a.id +
        '" title="Remover">×</button></td></tr>'
      );
    }).join("");

    var diario = d.diario_combate.map(function (g) {
      return "<p><strong>Rodada " + g.rodada + "</strong></p><ul>" +
        g.frases.map(function (f) { return "<li>" + f + "</li>"; }).join("") + "</ul>";
    }).join("");

    function ranking(lista) {
      if (!lista.length) return '<p class="ajuda">Sem dados ainda.</p>';
      return "<ol class=\"lista-ranking\">" + lista.map(function (par) {
        return "<li>" + escapeHtml(par[0]) + " — <strong>" + par[1] + "</strong></li>";
      }).join("") + "</ol>";
    }

    var r = d.resumo_combate;
    return (
      '<section class="pi-secao" id="pi-acoes"><h3>Ações (ataque, cura…)</h3>' + form +
      '<table class="tabela-combate"><thead><tr><th>Rodada</th><th>Quem</th><th>Ação</th><th>Com</th>' +
      "<th>Em quem</th><th>Valor</th><th>Obs.</th><th></th></tr></thead><tbody>" + linhasLog + "</tbody></table>" +
      "<h4>Diário de combate</h4>" + diario +
      '<h4>Resumo do combate</h4><div class="pi-grade-resumo">' +
      "<div><h5>Dano causado</h5>" + ranking(r.dano_causado) + "</div>" +
      "<div><h5>Dano recebido</h5>" + ranking(r.dano_recebido) + "</div>" +
      "<div><h5>Cura feita</h5>" + ranking(r.cura_feita) + "</div>" +
      "<div><h5>Mais golpes</h5>" + ranking(r.golpes) + "</div></div></section>"
    );
  };

  Widget.prototype._secaoPerigo = function () {
    return (
      '<section class="pi-secao pi-zona-perigo"><h3>Encerrar este combate</h3>' +
      '<p class="ajuda">Guarda tudo num arquivo com data e hora e começa do zero.</p>' +
      '<form data-acao="arquivar"><button type="submit" class="botao-secundario">' +
      "Arquivar e começar do zero</button></form></section>"
    );
  };

  // --------------------------------------------------------------------
  // Eventos — um listener de clique e um de submit no próprio elemento raiz
  // (delegação: cobre todo botão/formulário redesenhado a cada renderizar()).
  // --------------------------------------------------------------------

  Widget.prototype.ligarEventos = function () {
    var self = this;

    this.raiz.addEventListener("submit", function (ev) {
      var form = ev.target.closest("form[data-acao]");
      if (!form) return;
      ev.preventDefault();
      var acao = form.getAttribute("data-acao");
      var dadosForm = new FormData(form);
      var cid = form.getAttribute("data-cid");

      if (acao === "adicionar-nota") {
        self.chamar("POST", "/nota", { texto: dadosForm.get("texto") });
      } else if (acao === "salvar-resumo") {
        self.chamar("POST", "/resumo", { resumo: dadosForm.get("resumo") });
      } else if (acao === "adicionar-combatente") {
        var ficha = dadosForm.get("ficha") || "";
        var partesFicha = ficha.split("::");
        self.chamar("POST", "/combatente", {
          nome: dadosForm.get("nome"), tipo: dadosForm.get("tipo"),
          iniciativa: dadosForm.get("iniciativa"), pv_atual: dadosForm.get("pv_atual"),
          pv_maximo: dadosForm.get("pv_maximo"),
          ficha_pagina: partesFicha.length > 1 ? partesFicha[0] : "",
          ficha_slug: partesFicha.length > 1 ? partesFicha[1] : "",
        });
      } else if (acao === "ajustar-pv") {
        self.chamar("POST", "/combatente/" + cid + "/pv", { delta: dadosForm.get("delta") || 0 });
      } else if (acao === "atualizar-status") {
        self.chamar("POST", "/combatente/" + cid + "/status", { status: dadosForm.get("status") });
      } else if (acao === "proximo-turno") {
        self.chamar("POST", "/turno/proximo");
      } else if (acao === "registrar-acao") {
        self.chamar("POST", "/acao", {
          autor_id: dadosForm.get("autor_id"), tipo: dadosForm.get("tipo"),
          alvo_id: dadosForm.get("alvo_id"), meio: dadosForm.get("meio"),
          valor: dadosForm.get("valor"), obs: dadosForm.get("obs"),
        });
      } else if (acao === "arquivar") {
        if (window.confirm("Arquivar e limpar o combate desta página? A tela volta a ficar em branco.")) {
          self.chamar("POST", "/arquivar");
        }
      }
    });

    this.raiz.addEventListener("click", function (ev) {
      var botao = ev.target.closest("button[data-acao]");
      if (!botao) return;
      var acao = botao.getAttribute("data-acao");
      var cid = botao.getAttribute("data-cid");

      if (acao === "remover-nota") {
        self.chamar("POST", "/nota/" + botao.getAttribute("data-indice") + "/remover");
      } else if (acao === "flag-caido") {
        self.chamar("POST", "/combatente/" + cid + "/flag/caido");
      } else if (acao === "flag-morto") {
        self.chamar("POST", "/combatente/" + cid + "/flag/morto");
      } else if (acao === "remover-combatente") {
        self.chamar("POST", "/combatente/" + cid + "/remover");
      } else if (acao === "remover-acao") {
        self.chamar("POST", "/acao/" + botao.getAttribute("data-id") + "/remover");
      }
    });
  };

  function iniciar() {
    document.querySelectorAll(".painel-iniciativa[data-pagina]").forEach(function (raiz) {
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
