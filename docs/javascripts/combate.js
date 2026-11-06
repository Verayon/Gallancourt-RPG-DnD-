/* Combat Tracker embutido (ver admin/combate_api.py e hooks/gallancourt.py::_combate_dinamico) —
 * widget que roda dentro da `<div class="combate-painel ficha-personagem" data-pagina="...">` da
 * aba "Combat Tracker" de cada página de sessão, falando por fetch() com a API do banco
 * (admin/app.py, rotas /api/combate/...). Mesmo esqueleto de ficha.js: busca ao carregar,
 * redesenha a cada ação a partir da resposta. Substitui o antigo Painel de Iniciativa
 * (admin/sessao_viva.py + painel-iniciativa.js + alternancia-mestre.js).
 *
 * Em modo leitura (sem Modo Mestre): só a lista de participantes e o painel do token em foco,
 * sem nenhum controle de escrita. Em Modo Mestre: adicionar/remover participante, iniciativa,
 * grade de 15 condições por card, economia de ação, ataque/cura manual (d20 físico + bônus),
 * teste de resistência em área (modal), concentração, reações manuais, testes de morte, log e
 * o resumo pós-combate (XP + loot) ao encerrar.
 */
(function () {
  "use strict";

  var CONDICOES_D20 = [
    "Agarrado", "Apavorado", "Atordoado", "Caído", "Cego", "Enfeitiçado", "Envenenado",
    "Exausto", "Incapacitado", "Inconsciente", "Invisível", "Paralisado", "Petrificado",
    "Restringido", "Surdo",
  ];
  // Sigla de 3 letras por condição — únicas de propósito (não é só as 3 primeiras letras: Incapacitado
  // e Inconsciente colidiriam em "INC"). Mostrada no ícone pequeno do card; o nome completo vai no title.
  var SIGLA_CONDICAO = {
    "Agarrado": "AGR", "Apavorado": "APV", "Atordoado": "ATD", "Caído": "CAI", "Cego": "CGO",
    "Enfeitiçado": "ENF", "Envenenado": "EVN", "Exausto": "EXA", "Incapacitado": "ICP",
    "Inconsciente": "ICS", "Invisível": "INV", "Paralisado": "PRL", "Petrificado": "PTR",
    "Restringido": "RST", "Surdo": "SUR",
  };
  var TIPOS_ATOR = ["monstro", "npc", "jogador"];
  var ROTULOS_TIPO_ATOR = { monstro: "Monstro", npc: "NPC", jogador: "Jogador" };
  var SIGLAS_MOEDA = ["pc", "pp", "pe", "po", "pl"];

  function escapeHtml(valor) {
    return String(valor == null ? "" : valor)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  // Grade de pips (bolinha preenchida = espaço/carga disponível) pro pool de magia/item com carga
  // no painel do token — ver .combate-painel__pips/.pip em extra.css.
  function pips(total, preenchidos) {
    var out = "";
    for (var i = 0; i < total; i++) out += '<span class="pip' + (i < preenchidos ? " pip--on" : "") + '"></span>';
    return out;
  }

  function barraPv(atual, maximo, temporario, classeExtra) {
    var pct = maximo > 0 ? Math.max(0, Math.min(100, (atual / maximo) * 100)) : 0;
    var nivel = pct <= 25 ? "critico" : (pct <= 50 ? "ferido" : "ok");
    var texto = atual + "/" + maximo + (temporario ? " (+" + temporario + ")" : "");
    return (
      '<div class="combate-painel__barra-pv' + (classeExtra ? " " + classeExtra : "") + '">' +
      '<div class="combate-painel__barra-pv-preenchimento combate-painel__barra-pv-preenchimento--' + nivel + '" style="width:' + pct + '%"></div>' +
      '<span class="combate-painel__barra-pv-texto">PV ' + escapeHtml(texto) + "</span>" +
      "</div>"
    );
  }

  function Widget(raiz) {
    this.raiz = raiz;
    this.pagina = raiz.getAttribute("data-pagina");
    this.dados = null; // o objeto "combate", ou null se nenhum ativo
    this.autenticado = false;
    this.foco = null; // id do participante mostrado no Painel do Token
    this.alvos = {}; // id do participante -> true, pra ataque/cura/resistência
    this.busca = null; // { tipo, q, resultados, nomeExibicao, iniciativa }
    this.modal = null; // { tipo: "resistencia" } | { tipo: "resumo", xp, loot } | { tipo: "iniciar" }
    this.bloqueio = null; // { motivo, forcar() } — recurso sem espaço (ver _chamarComForca)
    this.ultimoResultado = "";
    this.encontros = []; // encontros planejados desta página (ver encontro.js), pra pré-carregar
    this.encontroEscolhido = "";
    this.ligarEventos();
    this.carregar();
  }

  Widget.prototype._url = function (caminho) {
    return "/api/combate/" + encodeURIComponent(this.pagina) + (caminho || "");
  };

  Widget.prototype.carregar = function () {
    var self = this;
    Promise.all([
      fetch(this._url()).then(function (r) { return r.json(); }),
      fetch("/api/auth/estado").then(function (r) { return r.json(); }).catch(function () { return { autenticado: false }; }),
      fetch("/api/encontros/" + encodeURIComponent(this.pagina)).then(function (r) { return r.json(); }).catch(function () { return { encontros: [] }; }),
    ]).then(function (resultados) {
      self.dados = resultados[0].combate;
      self.autenticado = !!resultados[1].autenticado;
      self.encontros = resultados[2].encontros || [];
      self.renderizar();
    }).catch(function (erro) {
      self.raiz.innerHTML = '<p class="ajuda">⚠️ Não consegui falar com o Painel do Mestre. ' +
        "Confirme que ele está rodando e recarregue a página. <small>(" + escapeHtml(erro && erro.message) + ")</small></p>";
    });
  };

  // Chama uma rota do combate e atualiza o estado a partir de `dados.combate` (mais qualquer
  // `ultimo_*` que a rota devolva, usado como feedback imediato de rolagem).
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
        self.dados = res.dados.combate !== undefined ? res.dados.combate : self.dados;
        self._atualizarUltimoResultado(res.dados);
        self.renderizar();
        return res.dados;
      })
      .catch(function (erro) { window.alert("Erro: " + erro.message); return null; });
  };

  // Conjurar magia / usar item com carga — bloqueia sem recurso disponível, com opção de forçar
  // (ver admin/combate_api.py::conjurar_magia/usar_carga_item). Sem espaço, não grava nada e guarda
  // o motivo em `this.bloqueio`; o painel do token mostra o banner "Ação bloqueada" com Cancelar/
  // Forçar (ver _painelToken) em vez do window.confirm() antigo.
  Widget.prototype._chamarComForca = function (caminho, corpo) {
    var self = this;
    return fetch(caminho, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.erro) { window.alert(d.erro); return; }
        if (d.resultado && d.resultado.bloqueado) {
          self.bloqueio = {
            motivo: d.resultado.motivo,
            forcar: function () {
              corpo.forcar = true;
              self.bloqueio = null;
              self._chamarComForca(caminho, corpo);
            },
          };
          self.renderizar();
          return;
        }
        self.bloqueio = null;
        self.dados = d.combate;
        self.renderizar();
      })
      .catch(function (erro) { window.alert("Erro: " + erro.message); });
  };

  Widget.prototype.conjurarMagia = function (participanteId, vinculoId, nivelSlot, forcar) {
    this._chamarComForca(
      "/api/combate/" + this.dados.id + "/participantes/" + participanteId + "/conjurar",
      { magia_vinculo_id: vinculoId, nivel_slot: nivelSlot, forcar: !!forcar },
    );
  };

  Widget.prototype.usarItem = function (participanteId, vinculoId, forcar) {
    this._chamarComForca(
      "/api/combate/" + this.dados.id + "/participantes/" + participanteId + "/usar-item",
      { equipamento_vinculo_id: vinculoId, forcar: !!forcar },
    );
  };

  Widget.prototype._atualizarUltimoResultado = function (dados) {
    if (dados.ultimo_ataque) {
      var a = dados.ultimo_ataque;
      this.ultimoResultado = "d20 " + a.d20 + " + " + a.bonus + " = " + a.total + " — " +
        a.alvos.map(function (al) { return (al.acertou ? "acertou" : "errou") + " (CA " + al.ca + ")"; }).join(", ");
    } else if (dados.ultima_reacao) {
      this.ultimoResultado = "Reação oferecida: " + dados.ultima_reacao.rotulo;
    } else if (dados.ultimo_teste_morte) {
      this.ultimoResultado = "Teste de morte: d20 " + dados.ultimo_teste_morte.d20 + " — " + dados.ultimo_teste_morte.efeito;
    } else if (dados.ultima_concentracao) {
      var c = dados.ultima_concentracao;
      this.ultimoResultado = "Concentração: CD " + c.cd + ", total " + c.total + " — " + (c.sucesso ? "manteve" : "perdeu a magia");
    }
  };

  // --------------------------------------------------------------------
  // Montagem do HTML
  // --------------------------------------------------------------------

  Widget.prototype.renderizar = function () {
    var c = this.dados;
    if (!c) {
      this.raiz.innerHTML = this._semCombate();
      return;
    }
    var html =
      this._cabecalho(c) +
      (this.ultimoResultado ? '<p class="ajuda combate-painel__ultimo-resultado">' + escapeHtml(this.ultimoResultado) + "</p>" : "") +
      (this.autenticado ? this._formAdicionar() : "") +
      '<div class="combate-painel__layout">' +
      '<div class="combate-painel__coluna-lista">' + this._listaParticipantes(c) + "</div>" +
      '<div class="combate-painel__coluna-token">' + this._painelToken(c) + "</div>" +
      "</div>" +
      (this.autenticado ? this._painelAcoes(c) : "") +
      this._painelLog(c) +
      (this.modal ? this._modal(c) : "");
    this.raiz.innerHTML = html;
  };

  Widget.prototype._semCombate = function () {
    if (!this.autenticado) {
      return '<p class="ajuda">Nenhum combate em andamento nesta sessão.</p>';
    }
    return (
      '<p class="ajuda">Nenhum combate em andamento nesta sessão.</p>' +
      '<button type="button" class="botao-principal" data-acao="abrir-iniciar-combate">Iniciar combate</button>' +
      (this.modal && this.modal.tipo === "iniciar" ? this._modalIniciarCombate() : "")
    );
  };

  // Modal de "Iniciar combate" — escolhe um encontro planejado (ver encontro.js/admin/encontro_api.py)
  // pra pré-carregar o tracker, ou começa vazio. Substitui o <select> solto por cartões clicáveis
  // com nome/contagem/prévia da ordem, mesma família .combate-modal já usada no resumo pós-combate.
  Widget.prototype._modalIniciarCombate = function () {
    var self = this;
    var sel = this.encontroEscolhido;
    var cartoes = this.encontros.map(function (e) {
      var ativo = String(e.id) === sel;
      var nomes = e.participantes.slice(0, 5).map(function (p) { return escapeHtml(p.nome); }).join(", ") +
        (e.participantes.length > 5 ? "…" : "");
      return (
        '<button type="button" class="combate-modal__opcao' + (ativo ? " combate-modal__opcao--sel" : "") +
        '" aria-pressed="' + ativo + '" data-acao="escolher-encontro-modal" data-encontro="' + e.id + '">' +
        "<strong>" + escapeHtml(e.nome) + "</strong> <span class=\"ajuda\">" + e.participantes.length + " participante(s)</span>" +
        (nomes ? "<br><span class=\"ajuda\">" + nomes + "</span>" : "") +
        "</button>"
      );
    }).join("");
    return (
      '<div class="combate-modal"><div class="combate-modal__caixa">' +
      '<button type="button" class="botao-remover combate-modal__fechar" data-acao="fechar-modal">× Fechar</button>' +
      "<h3>Iniciar combate</h3>" +
      (this.encontros.length
        ? '<div class="combate-modal__opcoes">' +
          '<button type="button" class="combate-modal__opcao' + (!sel ? " combate-modal__opcao--sel" : "") +
          '" aria-pressed="' + !sel + '" data-acao="escolher-encontro-modal" data-encontro="">' +
          "<strong>Começar vazio</strong> <span class=\"ajuda\">Sem encontro planejado</span></button>" +
          cartoes + "</div>"
        : '<p class="ajuda">Nenhum encontro planejado nesta sessão — vai começar vazio.</p>') +
      '<button type="button" class="botao-principal" data-acao="confirmar-iniciar-combate">Iniciar combate</button>' +
      "</div></div>"
    );
  };

  Widget.prototype._cabecalho = function (c) {
    var controles = this.autenticado
      ? '<button type="button" class="botao-secundario" data-acao="proximo-turno">Próximo turno</button>' +
        '<button type="button" class="botao-remover" data-acao="encerrar-combate">Encerrar combate</button>'
      : "";
    return (
      '<div class="combate-painel__cabecalho">' +
      '<span class="pilula pilula--ativa">Rodada ' + c.rodada + "</span>" +
      controles +
      "</div>"
    );
  };

  Widget.prototype._formAdicionar = function () {
    var b = this.busca;
    var abrir = b
      ? ""
      : '<button type="button" class="botao-secundario" data-acao="abrir-busca-participante">+ adicionar participante</button>';
    if (!b) return '<div class="combate-painel__grupo">' + abrir + "</div>";

    var opcoesTipo = TIPOS_ATOR.map(function (t) {
      return '<option value="' + t + '"' + (t === b.tipo ? " selected" : "") + ">" + ROTULOS_TIPO_ATOR[t] + "</option>";
    }).join("");
    var linhas = (b.resultados || []).map(function (p) {
      return p.fichas.map(function (f) {
        var rotulo = f.is_base ? p.nome : p.nome + " (" + f.rotulo + ")";
        var info = f.cr ? "CR " + f.cr : (f.nivel != null ? "Nível " + f.nivel : "");
        return (
          '<tr><td>' + escapeHtml(rotulo) + "</td><td>" + escapeHtml(info) + "</td><td>CA " + (f.ca_total != null ? f.ca_total : "—") +
          ", PV " + (f.pv_maximo != null ? f.pv_maximo : "—") + '</td>' +
          '<td><button type="button" class="botao-secundario" data-acao="usar-busca-participante" data-ficha="' + f.id + '">adicionar</button></td></tr>'
        );
      }).join("");
    }).join("");
    return (
      '<div class="combate-painel__grupo combate-painel__busca-participante">' +
      '<div class="combate-painel__busca-topo">' +
      '<select data-acao="tipo-busca-participante">' + opcoesTipo + "</select>" +
      '<input type="search" placeholder="Buscar por nome…" value="' + escapeHtml(b.q || "") + '" data-acao="q-busca-participante" autofocus>' +
      '<input type="text" class="input-medio" placeholder="Nome de exibição (opcional, ex.: Goblin 1)" value="' + escapeHtml(b.nomeExibicao || "") + '" data-acao="nome-busca-participante">' +
      '<input type="number" class="input-pequeno" placeholder="Iniciativa" value="' + (b.iniciativa || "") + '" data-acao="iniciativa-busca-participante">' +
      '<button type="button" class="botao-remover" data-acao="fechar-busca-participante" title="Fechar">× Fechar</button>' +
      "</div>" +
      (linhas
        ? '<table class="ficha-personagem__picker-tabela"><thead><tr><th>Nome</th><th>Nível/CR</th><th>CA/PV</th><th></th></tr></thead><tbody>' + linhas + "</tbody></table>"
        : '<p class="ajuda">Nada encontrado.</p>') +
      "</div>"
    );
  };

  Widget.prototype._listaParticipantes = function (c) {
    var self = this;
    var cartoes = c.participantes.map(function (p) { return self._cardParticipante(p, c); }).join("");
    return cartoes || '<p class="ajuda">Nenhum participante ainda.</p>';
  };

  Widget.prototype._cardParticipante = function (p, c) {
    var self = this;
    var daVez = c.turno_participante_id === p.id;
    var emFoco = this.foco === p.id;
    var alvoMarcado = !!this.alvos[p.id];
    var foto = p.foto
      ? '<img class="combate-painel__card-foto" src="' + escapeHtml(p.foto) + '" alt="">'
      : '<div class="combate-painel__card-foto combate-painel__card-foto--vazia"></div>';

    var condicoesGrade = this.autenticado
      ? CONDICOES_D20.map(function (nome) {
          var ativa = p.condicoes.indexOf(nome) !== -1;
          return '<button type="button" class="combate-painel__cond' + (ativa ? " combate-painel__cond--ativa" : "") +
            '" data-acao="alternar-condicao" data-participante="' + p.id + '" data-nome="' + escapeHtml(nome) + '" title="' + escapeHtml(nome) + '">' +
            escapeHtml(SIGLA_CONDICAO[nome] || nome.slice(0, 3)) + "</button>";
        }).join("")
      : p.condicoes.map(function (nome) { return '<span class="pilula pilula--ativa">' + escapeHtml(nome) + "</span>"; }).join("");

    var iniciativa = this.autenticado
      ? '<span class="chip-editavel"><strong>Inic.</strong>' +
        '<input type="number" class="input-pequeno" data-acao="iniciativa-base" data-participante="' + p.id + '" value="' + p.iniciativa_base + '"></span>' +
        '<span class="chip-editavel"><strong>Desemp.</strong>' +
        '<button type="button" class="chip-passo" data-acao="desempate" data-participante="' + p.id + '" data-passo="-1">−</button>' +
        "<span>" + p.iniciativa_desempate + "</span>" +
        '<button type="button" class="chip-passo" data-acao="desempate" data-participante="' + p.id + '" data-passo="1">+</button></span>'
      : '<span>Iniciativa ' + p.iniciativa_base + "</span>";

    var deathSaves = p.caido && !p.morto
      ? '<div class="combate-painel__death-saves">Sucessos: ' + p.death_save_sucessos + "/3 · Falhas: " + p.death_save_falhas + "/3" +
        (this.autenticado
          ? ' <button type="button" class="botao-secundario" data-acao="teste-morte" data-participante="' + p.id + '">Rolar teste de morte</button>'
          : "") +
        "</div>"
      : "";

    var acoesCard = this.autenticado
      ? '<label class="combate-painel__card-alvo"><input type="checkbox" data-acao="marcar-alvo" data-participante="' + p.id + '"' +
        (alvoMarcado ? " checked" : "") + "> alvo</label>" +
        '<button type="button" class="botao-remover" data-acao="remover-participante" data-participante="' + p.id + '" title="Remover">×</button>'
      : "";

    return (
      '<div class="combate-painel__card' + (daVez ? " combate-painel__card--davez" : "") + (emFoco ? " combate-painel__card--foco" : "") +
      (p.morto ? " combate-painel__card--morto" : "") + '" data-acao="focar" data-participante="' + p.id + '">' +
      '<div class="combate-painel__card-topo">' + foto +
      '<div class="combate-painel__card-info"><strong>' + escapeHtml(p.nome) + (p.morto ? " 💀" : (p.caido ? " 🩸" : "")) + "</strong>" +
      '<span class="combate-painel__ca-chip" title="Classe de Armadura"><strong>CA</strong> ' + p.ca_total + "</span>" +
      "<div>" + iniciativa + "</div></div></div>" +
      barraPv(p.pv_atual, p.pv_maximo, p.pv_temporario) +
      '<div class="combate-painel__card-condicoes">' + condicoesGrade + "</div>" +
      deathSaves +
      '<div class="combate-painel__card-acoes">' + acoesCard + "</div>" +
      "</div>"
    );
  };

  Widget.prototype._focoAtual = function (c) {
    var self = this;
    var id = this.foco || c.turno_participante_id;
    var p = c.participantes.filter(function (x) { return x.id === id; })[0];
    return p || c.participantes[0];
  };

  Widget.prototype._painelToken = function (c) {
    var p = this._focoAtual(c);
    if (!p) return '<p class="ajuda">Adicione participantes para começar.</p>';
    var editavel = this.autenticado;

    var acoes = p.habilidades.map(function (h) {
      var usar = (editavel && h.usos_maximo != null)
        ? ' <button type="button" class="botao-secundario" data-acao="usar-habilidade" data-ficha="' + p.ficha_id + '" data-vinculo="' + h.vinculo_id + '"' +
          (h.usos_restantes <= 0 ? " disabled" : "") + ">usar (" + h.usos_restantes + "/" + h.usos_maximo + ")</button>"
        : (h.usos_maximo != null ? ' <span class="ajuda">(' + h.usos_restantes + "/" + h.usos_maximo + " usos)</span>" : "");
      return "<li>" + (h.favorito ? "★ " : "") + "<strong>" + escapeHtml(h.nome) + "</strong>" + (h.bonus_acerto != null ? " (" + (h.bonus_acerto >= 0 ? "+" : "") + h.bonus_acerto + ")" : "") +
        (h.dano_formula ? " — " + escapeHtml(h.dano_formula) + " " + escapeHtml(h.dano_tipo || "") : "") + usar + "</li>";
    }).join("");
    var magias = p.magias.map(function (m) {
      var conjurar = editavel
        ? ' <input type="number" class="input-pequeno" min="' + (m.nivel || 0) + '" max="9" value="' + (m.nivel || 0) +
          '" data-nivel-slot="' + m.vinculo_id + '" title="Nível do espaço a gastar">' +
          ' <button type="button" class="chip" data-acao="conjurar-magia" data-participante="' + p.id + '" data-vinculo="' + m.vinculo_id + '">Conjurar</button>'
        : "";
      return "<li>" + (m.favorito ? "★ " : "") + "<strong>" + escapeHtml(m.nome) + "</strong>" + (m.nivel != null ? " (nível " + m.nivel + ")" : "") +
        (m.resistencia ? " — resistência: " + escapeHtml(m.resistencia) : "") + conjurar + "</li>";
    }).join("");
    var slots = (p.espacos_magia || []).map(function (e) {
      var restante = e.maximo - e.usado;
      return (
        '<span class="combate-painel__pool"><span class="lbl">Nv.' + e.nivel + (e.rotulo ? " " + escapeHtml(e.rotulo) : "") + "</span>" +
        '<span class="combate-painel__pips">' + pips(e.maximo, restante) + "</span>" +
        '<span class="ajuda">' + restante + "/" + e.maximo + "</span></span>"
      );
    }).join("");
    var itensCarga = (p.equipamentos || []).filter(function (e) { return e.cargas; }).map(function (e) {
      var usar = editavel
        ? ' <button type="button" class="chip' + (e.cargas.restante <= 0 ? " chip--gated" : "") +
          '" data-acao="usar-item" data-participante="' + p.id + '" data-vinculo="' + e.vinculo_id + '">usar</button>'
        : "";
      return (
        "<li>" + escapeHtml(e.nome) + ' <span class="combate-painel__pips">' + pips(e.cargas.maximo, e.cargas.restante) + "</span> " +
        e.cargas.restante + "/" + e.cargas.maximo + " cargas" + usar + "</li>"
      );
    }).join("");

    var economia = editavel
      ? ["acao_usada", "acao_bonus_usada", "reacao_usada", "movimento_usado"].map(function (campo, i) {
          var rotulos = ["1 Ação", "1 Ação Bônus", "1 Reação", "1 Movimento"];
          return '<label class="combate-painel__economia-item' + (p[campo] ? " combate-painel__economia-item--gasta" : "") + '">' +
            '<input type="checkbox" data-acao="economia-acao" data-participante="' + p.id + '" data-campo="' + campo + '"' +
            (p[campo] ? " checked" : "") + "> " + rotulos[i] + "</label>";
        }).join("")
      : "";

    var banner = (editavel && this.bloqueio)
      ? '<div class="combate-painel__bloqueio" role="alert">' +
        '<p class="combate-painel__bloqueio-titulo">Ação bloqueada · nada foi gravado</p>' +
        '<p>' + escapeHtml(this.bloqueio.motivo) + "</p>" +
        '<div class="combate-painel__bloqueio-acoes">' +
        '<button type="button" class="botao-secundario" data-acao="cancelar-bloqueio">Cancelar</button>' +
        '<button type="button" class="botao-remover" data-acao="forcar-bloqueio">Forçar mesmo assim</button>' +
        "</div></div>"
      : "";

    var concentracao = editavel
      ? '<span class="chip-editavel"><strong>Concentrando</strong>' +
        '<input type="text" class="input-medio" data-acao="concentracao" data-participante="' + p.id + '" value="' + escapeHtml(p.concentrando_em || "") + '" placeholder="(nenhuma)"></span>'
      : (p.concentrando_em ? '<span class="pilula">Concentrando: ' + escapeHtml(p.concentrando_em) + "</span>" : "");

    var reacao = editavel
      ? '<div class="combate-painel__reacao">' +
        '<input type="text" class="input-medio" data-reacao-rotulo placeholder="Contramagia / Esquiva Sobrenatural…">' +
        '<button type="button" class="botao-secundario" data-acao="oferecer-reacao" data-participante="' + p.id + '"' +
        (p.reacao_usada ? " disabled" : "") + ">Oferecer reação</button></div>"
      : "";

    return (
      '<div class="combate-painel__token">' +
      '<div class="combate-painel__token-cabecalho">' +
      (p.foto
        ? '<img class="combate-painel__card-foto combate-painel__card-foto--grande" src="' + escapeHtml(p.foto) + '" alt="">'
        : '<div class="combate-painel__card-foto combate-painel__card-foto--grande combate-painel__card-foto--vazia"></div>') +
      '<div class="combate-painel__token-titulo"><h4>' + escapeHtml(p.nome) + "</h4>" +
      '<span class="combate-painel__ca-chip" title="Classe de Armadura"><strong>CA</strong> ' + p.ca_total + "</span></div>" +
      "</div>" +
      banner +
      barraPv(p.pv_atual, p.pv_maximo, p.pv_temporario, "combate-painel__barra-pv--grande") +
      (concentracao ? '<div class="combate-painel__grupo">' + concentracao + "</div>" : "") +
      (economia ? '<div class="combate-painel__economia">' + economia + "</div>" : "") +
      reacao +
      (slots ? '<div class="combate-painel__grupo"><strong>Espaços de magia</strong><br>' + slots + "</div>" : "") +
      (acoes ? '<div class="combate-painel__grupo"><strong>Ações/Traços</strong><ul class="ficha-personagem__lista-simples">' + acoes + "</ul></div>" : "") +
      (magias ? '<div class="combate-painel__grupo"><strong>Magias</strong><ul class="ficha-personagem__lista-simples">' + magias + "</ul></div>" : "") +
      (itensCarga ? '<div class="combate-painel__grupo"><strong>Itens com carga</strong><ul class="ficha-personagem__lista-simples">' + itensCarga + "</ul></div>" : "") +
      "</div>"
    );
  };

  Widget.prototype._painelAcoes = function (c) {
    var nAlvos = Object.keys(this.alvos).filter(function (k) { return this.alvos[k]; }, this).length;
    return (
      '<div class="combate-painel__grupo combate-painel__ataque">' +
      "<strong>Ataque / Cura</strong> <span class=\"ajuda\">(" + nAlvos + " alvo(s) marcado(s) nos cards)</span><br>" +
      '<input type="number" class="input-pequeno" placeholder="d20" data-ataque-campo="d20" value="10">' +
      '<input type="number" class="input-pequeno" placeholder="bônus" data-ataque-campo="bonus" value="0">' +
      '<input type="number" class="input-pequeno" placeholder="dano/cura" data-ataque-campo="dano" value="0">' +
      '<label><input type="checkbox" data-ataque-campo="cura"> é cura</label>' +
      '<button type="button" class="botao-principal" data-acao="resolver-ataque">Resolver</button>' +
      '<button type="button" class="botao-secundario" data-acao="abrir-resistencia">Teste de resistência em área…</button>' +
      "</div>"
    );
  };

  Widget.prototype._painelLog = function (c) {
    var linhas = c.log.map(function (e) {
      var hora = "";
      try {
        var d = new Date(e.criado_em);
        hora = ("0" + d.getHours()).slice(-2) + ":" + ("0" + d.getMinutes()).slice(-2);
      } catch (ignorar) { hora = ""; }
      return "<li>" + (hora ? '<span class="ajuda">[' + hora + "] </span>" : "") +
        "<strong>Rodada " + e.rodada + "</strong> — " + escapeHtml(e.texto) + "</li>";
    }).join("");
    var controlesEscrita = this.autenticado
      ? '<div class="combate-painel__log-novo">' +
        '<input type="text" class="input-medio" placeholder="Anotar no log…" data-log-texto>' +
        '<button type="button" class="botao-secundario" data-acao="registrar-log">+ registrar</button>' +
        "</div>"
      : "";
    return (
      '<details class="combate-painel__grupo combate-painel__log"><summary><strong>Log de combate</strong></summary>' +
      controlesEscrita +
      (linhas ? '<ul class="ficha-personagem__lista-simples">' + linhas + "</ul>" : '<p class="ajuda">Vazio.</p>') +
      '<a class="botao-secundario" href="/api/combate/' + c.id + '/log/exportar?formato=txt" target="_blank">Exportar TXT</a> ' +
      '<a class="botao-secundario" href="/api/combate/' + c.id + '/log/exportar?formato=json" target="_blank">Exportar JSON</a>' +
      "</details>"
    );
  };

  Widget.prototype._modal = function (c) {
    if (this.modal.tipo === "resistencia") return this._modalResistencia(c);
    if (this.modal.tipo === "resumo") return this._modalResumo(c);
    return "";
  };

  Widget.prototype._modalResistencia = function (c) {
    var self = this;
    var alvos = c.participantes.filter(function (p) { return self.alvos[p.id]; });
    var linhas = alvos.map(function (p) {
      return (
        '<tr><td>' + escapeHtml(p.nome) + '</td>' +
        '<td><input type="number" class="input-pequeno" data-resistencia-d20="' + p.id + '" value="10"></td>' +
        '<td><input type="number" class="input-pequeno" data-resistencia-dano="' + p.id + '" value="0"></td></tr>'
      );
    }).join("");
    return (
      '<div class="combate-modal"><div class="combate-modal__caixa">' +
      '<button type="button" class="botao-remover combate-modal__fechar" data-acao="fechar-modal">× Fechar</button>' +
      "<h3>Teste de resistência em área</h3>" +
      '<label>CD <input type="number" class="input-pequeno" data-resistencia-cd value="10"></label> ' +
      '<label><input type="checkbox" data-resistencia-meio checked> metade do dano no sucesso</label><br>' +
      '<label>Condição aplicada em quem falha (opcional) <select data-resistencia-condicao><option value="">(nenhuma)</option>' +
      CONDICOES_D20.map(function (n) { return "<option>" + n + "</option>"; }).join("") + "</select></label>" +
      (linhas
        ? '<table class="ficha-personagem__picker-tabela"><thead><tr><th>Alvo</th><th>d20</th><th>Dano</th></tr></thead><tbody>' + linhas + "</tbody></table>"
        : '<p class="ajuda">Marque alvos nos cards antes de abrir este teste.</p>') +
      '<button type="button" class="botao-principal" data-acao="resolver-resistencia">Resolver</button>' +
      "</div></div>"
    );
  };

  Widget.prototype._modalResumo = function (c) {
    var modal = this.modal;
    var xp = modal.xp || { xp_por_jogador: 0, xp_total: 0, jogadores: [] };
    var loot = modal.loot || { itens: [], moedas: {} };
    var jogadores = xp.jogadores || [];
    var opcoesJogadores = jogadores.map(function (j) { return '<option value="' + j.ficha_id + '">' + escapeHtml(j.nome) + "</option>"; }).join("");

    var linhaLoot = function (idx, descricao, quantidade, dadosExtra) {
      return (
        '<tr data-loot-linha="' + idx + '" ' + dadosExtra + '>' +
        '<td><input type="checkbox" data-loot-incluir checked></td>' +
        "<td>" + escapeHtml(descricao) + "</td>" +
        '<td><input type="number" class="input-pequeno" data-loot-quantidade value="' + quantidade + '"></td>' +
        '<td><label><input type="radio" name="loot-modo-' + idx + '" value="dividir" checked data-loot-modo> dividir</label> ' +
        '<label><input type="radio" name="loot-modo-' + idx + '" value="individual" data-loot-modo> <select data-loot-jogador disabled>' + opcoesJogadores + "</select></label></td>" +
        "</tr>"
      );
    };
    var idx = 0;
    var linhasMoeda = SIGLAS_MOEDA.filter(function (s) { return loot.moedas["moeda_" + s] > 0; })
      .map(function (s) { return linhaLoot(idx++, loot.moedas["moeda_" + s] + " " + s.toUpperCase(), loot.moedas["moeda_" + s], 'data-loot-tipo="moeda" data-loot-campo-moeda="moeda_' + s + '"'); })
      .join("");
    var linhasItem = loot.itens.map(function (item) {
      return linhaLoot(idx++, item.nome, item.quantidade, 'data-loot-tipo="item" data-loot-equipamento="' + item.equipamento_id + '"');
    }).join("");

    return (
      '<div class="combate-modal"><div class="combate-modal__caixa combate-modal__caixa--larga">' +
      '<button type="button" class="botao-remover combate-modal__fechar" data-acao="fechar-modal">× Fechar</button>' +
      "<h3>Resumo pós-combate</h3>" +
      "<h4>Experiência</h4>" +
      "<p>XP total dos inimigos derrotados: <strong>" + xp.xp_total + "</strong> ÷ " + Math.max(1, jogadores.length) + " jogador(es)</p>" +
      '<label>XP por jogador <input type="number" class="input-medio" data-resumo-xp value="' + xp.xp_por_jogador + '"></label>' +
      '<button type="button" class="botao-principal" data-acao="distribuir-xp">Distribuir XP</button> ' +
      '<button type="button" class="botao-secundario" data-acao="pular-xp">Pular</button>' +
      "<h4>Espólios recolhidos</h4>" +
      (linhasMoeda + linhasItem
        ? '<table class="ficha-personagem__picker-tabela"><thead><tr><th>Incluir</th><th>Item</th><th>Qtd.</th><th>Destino</th></tr></thead><tbody>' +
          linhasMoeda + linhasItem + "</tbody></table>" +
          '<button type="button" class="botao-principal" data-acao="aplicar-loot">Enviar para Inventário do Grupo</button>'
        : '<p class="ajuda">Nenhum espólio — nenhum monstro morto nesta luta.</p>') +
      "</div></div>"
    );
  };

  // --------------------------------------------------------------------
  // Eventos
  // --------------------------------------------------------------------

  Widget.prototype.buscarParticipantes = function () {
    var self = this;
    var b = this.busca;
    fetch("/api/personagens-busca?tipo=" + encodeURIComponent(b.tipo) + "&q=" + encodeURIComponent(b.q || ""))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!self.busca) return;
        self.busca.resultados = d.itens || [];
        self.renderizar();
      });
  };

  Widget.prototype.ligarEventos = function () {
    var self = this;

    this.raiz.addEventListener("input", function (ev) {
      var alvo = ev.target;
      if (alvo.matches("[data-acao='q-busca-participante']")) {
        self.busca.q = alvo.value;
        window.clearTimeout(self._buscaTimer);
        self._buscaTimer = window.setTimeout(function () { self.buscarParticipantes(); }, 250);
      } else if (alvo.matches("[data-acao='nome-busca-participante']")) {
        self.busca.nomeExibicao = alvo.value;
      } else if (alvo.matches("[data-acao='iniciativa-busca-participante']")) {
        self.busca.iniciativa = alvo.value;
      }
    });

    this.raiz.addEventListener("change", function (ev) {
      var alvo = ev.target;
      if (alvo.matches("[data-acao='tipo-busca-participante']")) {
        self.busca.tipo = alvo.value;
        self.buscarParticipantes();
      } else if (alvo.matches("[data-acao='iniciativa-base']")) {
        self.chamar("PUT", "/api/combate/" + self.dados.id + "/participantes/" + alvo.getAttribute("data-participante") + "/iniciativa", { base: alvo.value });
      } else if (alvo.matches("[data-acao='economia-acao']")) {
        self.chamar("POST", "/api/combate/" + self.dados.id + "/participantes/" + alvo.getAttribute("data-participante") + "/economia-acao", { campo: alvo.getAttribute("data-campo") });
      } else if (alvo.matches("[data-acao='marcar-alvo']")) {
        var pid = alvo.getAttribute("data-participante");
        self.alvos[pid] = alvo.checked;
        self.renderizar();
      } else if (alvo.matches("[data-acao='concentracao']")) {
        self.chamar("PUT", "/api/combate/" + self.dados.id + "/participantes/" + alvo.getAttribute("data-participante") + "/concentracao", { nome: alvo.value || null });
      } else if (alvo.matches("[data-loot-modo]")) {
        var linha = alvo.closest("tr");
        var selecao = linha.querySelector("[data-loot-jogador]");
        if (selecao) selecao.disabled = alvo.value !== "individual";
      }
    });

    this.raiz.addEventListener("click", function (ev) {
      var passo = ev.target.closest("button[data-acao='desempate']");
      if (passo) {
        var delta = parseInt(passo.getAttribute("data-passo"), 10);
        self.chamar("PUT", "/api/combate/" + self.dados.id + "/participantes/" + passo.getAttribute("data-participante") + "/iniciativa",
          { desempate: self._desempateAtual(passo.getAttribute("data-participante")) + delta });
        return;
      }

      var card = ev.target.closest("[data-acao='focar']");
      if (card && !ev.target.closest("input, button, select, label")) {
        self.foco = parseInt(card.getAttribute("data-participante"), 10);
        self.bloqueio = null;
        self.renderizar();
        return;
      }

      var botao = ev.target.closest("button[data-acao]");
      if (!botao) return;
      var acao = botao.getAttribute("data-acao");
      var pid = botao.getAttribute("data-participante");
      var cid = self.dados && self.dados.id;

      if (acao === "abrir-iniciar-combate") {
        self.modal = { tipo: "iniciar" };
        self.renderizar();
      } else if (acao === "escolher-encontro-modal") {
        self.encontroEscolhido = botao.getAttribute("data-encontro") || "";
        self.renderizar();
      } else if (acao === "confirmar-iniciar-combate") {
        self.chamar("POST", self._url("/iniciar"), self.encontroEscolhido ? { encontro_id: self.encontroEscolhido } : undefined)
          .then(function (ok) { if (ok) { self.modal = null; self.renderizar(); } });
      } else if (acao === "proximo-turno") {
        self.chamar("POST", "/api/combate/" + self.dados.id + "/turno/proximo");
      } else if (acao === "encerrar-combate") {
        self.abrirResumo();
      } else if (acao === "abrir-busca-participante") {
        self.busca = { tipo: "monstro", q: "", resultados: [], nomeExibicao: "", iniciativa: "" };
        self.renderizar();
      } else if (acao === "fechar-busca-participante") {
        self.busca = null;
        self.renderizar();
      } else if (acao === "usar-busca-participante") {
        self.chamar("POST", "/api/combate/" + self.dados.id + "/participantes", {
          ficha_id: botao.getAttribute("data-ficha"),
          nome_exibicao: self.busca.nomeExibicao,
          iniciativa_base: self.busca.iniciativa || 0,
        }).then(function (ok) { if (ok) { self.busca = null; self.renderizar(); } });
      } else if (acao === "remover-participante") {
        if (!window.confirm("Remover este participante do combate?")) return;
        self.chamar("DELETE", "/api/combate/" + self.dados.id + "/participantes/" + pid);
      } else if (acao === "alternar-condicao") {
        self.chamar("POST", "/api/combate/" + self.dados.id + "/participantes/" + botao.getAttribute("data-participante") + "/condicoes", { nome: botao.getAttribute("data-nome") });
      } else if (acao === "usar-habilidade") {
        fetch("/api/fichas/" + botao.getAttribute("data-ficha") + "/habilidades/" + botao.getAttribute("data-vinculo") + "/usar", { method: "POST" })
          .then(function () { self.carregar(); });
      } else if (acao === "conjurar-magia") {
        var vinculoMagia = botao.getAttribute("data-vinculo");
        var nivelInput = self.raiz.querySelector('[data-nivel-slot="' + vinculoMagia + '"]');
        self.conjurarMagia(pid, vinculoMagia, nivelInput ? parseInt(nivelInput.value, 10) || 0 : 0, false);
      } else if (acao === "usar-item") {
        self.usarItem(pid, botao.getAttribute("data-vinculo"), false);
      } else if (acao === "cancelar-bloqueio") {
        self.bloqueio = null;
        self.renderizar();
      } else if (acao === "forcar-bloqueio") {
        if (self.bloqueio) self.bloqueio.forcar();
      } else if (acao === "oferecer-reacao") {
        var rotuloInput = botao.closest(".combate-painel__reacao").querySelector("[data-reacao-rotulo]");
        var rotulo = (rotuloInput.value || "").trim() || "Reação";
        if (!window.confirm('Usar a reação de ' + self._focoAtual(self.dados).nome + ' para "' + rotulo + '"?')) return;
        self.chamar("POST", "/api/combate/" + self.dados.id + "/participantes/" + pid + "/reacao", { rotulo: rotulo });
      } else if (acao === "teste-morte") {
        var d20 = window.prompt("Rolagem manual do d20 físico (teste de morte):", "10");
        if (d20 === null) return;
        self.chamar("POST", "/api/combate/" + self.dados.id + "/participantes/" + pid + "/teste-morte", { d20: d20 });
      } else if (acao === "resolver-ataque") {
        self.resolverAtaque();
      } else if (acao === "abrir-resistencia") {
        self.modal = { tipo: "resistencia" };
        self.renderizar();
      } else if (acao === "resolver-resistencia") {
        self.resolverResistencia();
      } else if (acao === "fechar-modal") {
        self.modal = null;
        self.renderizar();
      } else if (acao === "registrar-log") {
        var textoLog = self.raiz.querySelector("[data-log-texto]");
        if (!textoLog.value.trim()) return;
        self.chamar("POST", "/api/combate/" + self.dados.id + "/log", { texto: textoLog.value });
      } else if (acao === "distribuir-xp") {
        var xpInput = self.raiz.querySelector("[data-resumo-xp]");
        fetch("/api/combate/" + cid + "/distribuir-xp", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ xp_por_jogador: xpInput.value }),
        }).then(function () { window.alert("XP distribuído."); self.modal = null; self.dados = null; self.renderizar(); });
      } else if (acao === "pular-xp") {
        self.modal = null;
        self.dados = null;
        self.renderizar();
      } else if (acao === "aplicar-loot") {
        self.aplicarLoot();
      }
    });
  };

  Widget.prototype._desempateAtual = function (pid) {
    var p = this.dados.participantes.filter(function (x) { return String(x.id) === String(pid); })[0];
    return p ? p.iniciativa_desempate : 0;
  };

  Widget.prototype._alvosMarcados = function () {
    var self = this;
    return Object.keys(this.alvos).filter(function (k) { return self.alvos[k]; }).map(function (k) { return parseInt(k, 10); });
  };

  Widget.prototype.resolverAtaque = function () {
    var self = this;
    var ler = function (campo) { return self.raiz.querySelector("[data-ataque-campo='" + campo + "']").value; };
    var cura = self.raiz.querySelector("[data-ataque-campo='cura']").checked;
    var alvosAntes = this.dados.participantes.filter(function (p) { return self.alvos[p.id] && p.concentrando_em; });
    var alvosIds = this._alvosMarcados();
    if (!alvosIds.length) { window.alert("Marque ao menos um alvo nos cards."); return; }
    this.chamar("POST", "/api/combate/" + this.dados.id + "/ataque", {
      alvos: alvosIds, d20: ler("d20"), bonus: ler("bonus"), dano: ler("dano"), cura: cura,
    }).then(function (dados) {
      if (!dados) return;
      alvosAntes.forEach(function (p) { self._checarConcentracaoPrompt(p); });
    });
  };

  Widget.prototype._checarConcentracaoPrompt = function (participanteAntes) {
    var self = this;
    var d20 = window.prompt(
      participanteAntes.nome + " estava concentrando em \"" + participanteAntes.concentrando_em +
      "\" e sofreu dano. Rolagem manual do teste de concentração (d20):", "10",
    );
    if (d20 === null) return;
    var bonus = window.prompt("Bônus de Constituição (modificador + proficiência, se tiver):", "0") || 0;
    fetch("/api/combate/" + this.dados.id + "/participantes/" + participanteAntes.id + "/concentracao/teste", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ d20: d20, bonus: bonus, dano: 0 }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.erro) return;
      self.dados = d.combate;
      self._atualizarUltimoResultado(d);
      self.renderizar();
    });
  };

  Widget.prototype.resolverResistencia = function () {
    var self = this;
    var cd = this.raiz.querySelector("[data-resistencia-cd]").value;
    var meio = this.raiz.querySelector("[data-resistencia-meio]").checked;
    var condicao = this.raiz.querySelector("[data-resistencia-condicao]").value || null;
    var alvos = this._alvosMarcados().map(function (pid) {
      return {
        participante_id: pid,
        d20_bruto: self.raiz.querySelector('[data-resistencia-d20="' + pid + '"]').value,
        dano: self.raiz.querySelector('[data-resistencia-dano="' + pid + '"]').value,
      };
    });
    this.chamar("POST", "/api/combate/" + this.dados.id + "/resistencia", {
      cd: cd, meio_no_sucesso: meio, condicao_no_erro: condicao, alvos: alvos,
    }).then(function (ok) { if (ok) { self.modal = null; self.renderizar(); } });
  };

  Widget.prototype.abrirResumo = function () {
    var self = this;
    fetch("/api/combate/" + this.dados.id + "/resumo").then(function (r) { return r.json(); }).then(function (d) {
      self.modal = { tipo: "resumo", xp: d.xp, loot: d.loot };
      self.renderizar();
    });
  };

  Widget.prototype.aplicarLoot = function () {
    var self = this;
    var escolhas = [];
    this.raiz.querySelectorAll("[data-loot-linha]").forEach(function (linha) {
      if (!linha.querySelector("[data-loot-incluir]").checked) return;
      var modo = linha.querySelector("[data-loot-modo]:checked").value;
      var escolha = {
        tipo: linha.getAttribute("data-loot-tipo"),
        quantidade: linha.querySelector("[data-loot-quantidade]").value,
        modo: modo,
      };
      if (escolha.tipo === "moeda") escolha.campo_moeda = linha.getAttribute("data-loot-campo-moeda");
      else escolha.equipamento_id = parseInt(linha.getAttribute("data-loot-equipamento"), 10);
      if (modo === "individual") escolha.ficha_id = parseInt(linha.querySelector("[data-loot-jogador]").value, 10);
      escolhas.push(escolha);
    });
    var cid = this.dados.id;
    fetch("/api/combate/" + cid + "/aplicar-loot", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ escolhas: escolhas }),
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.erro) { window.alert(d.erro); return; }
      window.alert("Espólios enviados.");
      self.modal = null;
      self.dados = null;
      self.renderizar();
    });
  };

  function iniciar() {
    document.querySelectorAll(".combate-painel[data-pagina]").forEach(function (raiz) {
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
