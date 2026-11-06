/* Master's Shield — fundação (nome temporário, ver .claude/contexto/combate.md). Widget que roda
 * dentro da `<div class="sessao-viva-painel ficha-personagem" data-pagina="...">`, na mesma aba
 * de sessão onde o Combat Tracker (combate.js) continua existindo, aninhado, abaixo deste painel.
 * Fica sempre visível (calendário/localidade/log de interações), não só quando há combate — ver
 * hooks/gallancourt.py::_sessao_viva_dinamica e admin/sessao_viva_api.py. Mesmo esqueleto de
 * encontro.js: busca ao carregar, redesenha a cada ação a partir da resposta.
 */
(function () {
  "use strict";

  var ROTULOS_TIPO_INTERACAO = {
    teste_habilidade: "Teste de perícia", ataque: "Ataque", dano: "Dano", cura: "Cura",
    dialogo: "Diálogo", xp: "XP", loot: "Loot", evento_livre: "Evento livre",
  };
  var ROTULOS_PAPEL = { ator: "Ator", alvo: "Alvo", testemunha: "Testemunha" };
  var TIPOS_ATOR = ["monstro", "npc", "jogador"];
  var ROTULOS_TIPO_ATOR = { monstro: "Monstro", npc: "NPC", jogador: "Jogador" };

  function escapeHtml(valor) {
    return String(valor == null ? "" : valor)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function Widget(raiz) {
    this.raiz = raiz;
    this.pagina = raiz.getAttribute("data-pagina");
    this.sessaoViva = null;
    this.interacoes = [];
    this.lugares = [];
    this.autenticado = false;
    this.editandoTempo = null; // {ano, mes, dia, hora, minuto} (strings do form) ou null
    this.novoLugar = null; // {nome, lugarPaiId} ou null
    this.novaInteracao = null; // estado do form de registrar interação, ou null
    this.ligarEventos();
    this.carregar();
  }

  Widget.prototype._url = function (caminho) {
    return "/api/sessao-viva/" + encodeURIComponent(this.pagina) + (caminho || "");
  };

  Widget.prototype.carregar = function () {
    var self = this;
    Promise.all([
      fetch(this._url()).then(function (r) { return r.json(); }),
      fetch("/api/sessao-viva/lugares").then(function (r) { return r.json(); }),
      fetch("/api/auth/estado").then(function (r) { return r.json(); }).catch(function () { return { autenticado: false }; }),
    ]).then(function (resultados) {
      self.sessaoViva = resultados[0].sessao_viva;
      self.interacoes = resultados[0].interacoes || [];
      self.lugares = resultados[1].lugares || [];
      self.autenticado = !!resultados[2].autenticado;
      self.renderizar();
    }).catch(function (erro) {
      self.raiz.innerHTML = '<p class="ajuda">⚠️ Não consegui falar com o Painel do Mestre. ' +
        "Confirme que ele está rodando e recarregue a página. <small>(" + escapeHtml(erro && erro.message) + ")</small></p>";
    });
  };

  Widget.prototype.chamar = function (metodo, caminho, corpo) {
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

  // ------------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------------

  Widget.prototype.renderizar = function () {
    this.raiz.innerHTML =
      '<div class="sessao-viva__grade">' +
      this._blocoCalendario() + this._blocoLocalidade() +
      "</div>" + this._blocoLog();
  };

  Widget.prototype._nomeLugar = function (lugar) {
    if (!lugar) return null;
    var pai = lugar.lugar_pai_id ? this._lugarPorId(lugar.lugar_pai_id) : null;
    var base = (pai ? pai.nome + " › " : "") + lugar.nome;
    return lugar.canonico ? base : base + " (provisório)";
  };

  Widget.prototype._lugarPorId = function (id) {
    for (var i = 0; i < this.lugares.length; i++) {
      if (this.lugares[i].id === id) return this.lugares[i];
    }
    return null;
  };

  Widget.prototype._blocoCalendario = function () {
    var v = this.sessaoViva || {};
    if (this.editandoTempo) {
      var t = this.editandoTempo;
      return (
        '<div class="sessao-viva__bloco">' +
        '<h4>📅 Calendário</h4>' +
        '<div class="sessao-viva__form-tempo">' +
        '<input type="number" class="input-pequeno" placeholder="Ano" value="' + escapeHtml(t.ano) + '" data-acao="tempo-ano">' +
        '<input type="text" class="input-medio" placeholder="Mês" value="' + escapeHtml(t.mes) + '" data-acao="tempo-mes">' +
        '<input type="number" class="input-pequeno" placeholder="Dia" value="' + escapeHtml(t.dia) + '" data-acao="tempo-dia">' +
        '<input type="number" class="input-pequeno" placeholder="Hora" value="' + escapeHtml(t.hora) + '" data-acao="tempo-hora">' +
        '<input type="number" class="input-pequeno" placeholder="Min" value="' + escapeHtml(t.minuto) + '" data-acao="tempo-minuto">' +
        '<button type="button" class="botao-principal" data-acao="salvar-tempo">Salvar</button> ' +
        '<button type="button" class="botao-secundario" data-acao="cancelar-tempo">Cancelar</button>' +
        "</div></div>"
      );
    }
    var temData = v.ano || v.dia || v.hora != null;
    var texto = temData
      ? "Dia " + (v.dia || "?") + " de " + (v.mes || "?") + " de " + (v.ano || "?") +
        ", " + (v.hora != null ? String(v.hora).padStart(2, "0") : "??") + ":" +
        (v.minuto != null ? String(v.minuto).padStart(2, "0") : "??")
      : "Calendário ainda não definido nesta sessão.";
    return (
      '<div class="sessao-viva__bloco">' +
      '<h4>📅 Calendário</h4>' +
      '<p class="sessao-viva__momento">' + escapeHtml(texto) + "</p>" +
      (this.autenticado
        ? '<div class="sessao-viva__acoes">' +
          '<button type="button" class="botao-secundario" data-acao="avancar-tempo" data-minutos="10">+10 min</button>' +
          '<button type="button" class="botao-secundario" data-acao="avancar-tempo" data-minutos="60">+1 hora</button>' +
          '<button type="button" class="botao-secundario" data-acao="descanso-curto">Descanso curto</button>' +
          '<button type="button" class="botao-secundario" data-acao="descanso-longo">Descanso longo</button>' +
          '<button type="button" class="botao-secundario" data-acao="editar-tempo">✎ Editar</button>' +
          "</div>"
        : "") +
      "</div>"
    );
  };

  Widget.prototype._blocoLocalidade = function () {
    var self = this;
    var v = this.sessaoViva || {};
    var nomeAtual = this._nomeLugar(v.lugar_atual) || "—";
    var opcoes = '<option value="">— nenhum —</option>' + this.lugares.map(function (l) {
      return '<option value="' + l.id + '"' + (l.id === v.lugar_atual_id ? " selected" : "") + ">" +
        escapeHtml(self._nomeLugar(l)) + "</option>";
    }).join("");
    var formNovo = this.novoLugar
      ? '<div class="sessao-viva__form-lugar">' +
        '<input type="text" class="input-medio" placeholder="Nome do local (ex.: Loja do Alquimista)" ' +
        'value="' + escapeHtml(this.novoLugar.nome) + '" data-acao="novo-lugar-nome">' +
        '<select data-acao="novo-lugar-pai"><option value="">— sem lugar pai —</option>' +
        this.lugares.map(function (l) {
          return '<option value="' + l.id + '"' + (String(l.id) === String(self.novoLugar.lugarPaiId) ? " selected" : "") + ">" +
            escapeHtml(self._nomeLugar(l)) + "</option>";
        }).join("") + "</select>" +
        '<button type="button" class="botao-principal" data-acao="salvar-novo-lugar">Criar</button> ' +
        '<button type="button" class="botao-secundario" data-acao="cancelar-novo-lugar">Cancelar</button>' +
        "</div>"
      : "";
    return (
      '<div class="sessao-viva__bloco">' +
      '<h4>📍 Localidade</h4>' +
      '<p class="sessao-viva__momento">' + escapeHtml(nomeAtual) + "</p>" +
      (this.autenticado
        ? '<div class="sessao-viva__acoes">' +
          '<select data-acao="escolher-lugar">' + opcoes + "</select> " +
          '<button type="button" class="botao-secundario" data-acao="abrir-novo-lugar">+ local provisório</button>' +
          "</div>" + formNovo
        : "") +
      "</div>"
    );
  };

  Widget.prototype._cartaoInteracao = function (i) {
    var momento = (i.dia ? "dia " + i.dia + " " : "") + (i.hora != null ? String(i.hora).padStart(2, "0") + ":" + String(i.minuto || 0).padStart(2, "0") : "");
    var participantes = (i.participantes || []).map(function (p) {
      return escapeHtml(p.nome) + " (" + escapeHtml(ROTULOS_PAPEL[p.papel] || p.papel) + ")";
    }).join(", ");
    var rolagens = (i.rolagens || []).map(function (r) {
      return '<span class="pilula">' + escapeHtml(r.dado) + " → " + escapeHtml(r.resultado_total) + (r.online ? " 🎲" : "") + "</span>";
    }).join(" ");
    return (
      '<li class="sessao-viva__interacao">' +
      '<span class="pilula">' + escapeHtml(ROTULOS_TIPO_INTERACAO[i.tipo] || i.tipo) + "</span> " +
      (momento ? '<span class="ajuda">' + escapeHtml(momento) + "</span> " : "") +
      (i.lugar_nome ? '<span class="ajuda">em ' + escapeHtml(i.lugar_nome) + "</span> " : "") +
      (i.descricao ? "<br>" + escapeHtml(i.descricao) : "") +
      (i.pericia_ou_atributo ? "<br><span class=\"ajuda\">" + escapeHtml(i.pericia_ou_atributo) +
        (i.cd != null ? " (CD " + i.cd + ")" : "") +
        (i.sucesso != null ? (i.sucesso ? " — sucesso" : " — falha") : "") + "</span>" : "") +
      (participantes ? "<br><span class=\"ajuda\">" + participantes + "</span>" : "") +
      (rolagens ? "<br>" + rolagens : "") +
      "</li>"
    );
  };

  Widget.prototype._blocoLog = function () {
    var self = this;
    var lista = this.interacoes.map(function (i) { return self._cartaoInteracao(i); }).join("");
    return (
      '<div class="sessao-viva__bloco sessao-viva__bloco--log">' +
      '<h4>📜 Log de interações</h4>' +
      '<ul class="sessao-viva__lista-interacoes">' + (lista || '<li class="ajuda">Nenhuma interação registrada ainda.</li>') + "</ul>" +
      (this.autenticado ? this._formInteracao() : "") +
      "</div>"
    );
  };

  Widget.prototype._formInteracao = function () {
    var ni = this.novaInteracao;
    if (!ni) {
      return '<button type="button" class="botao-secundario" data-acao="abrir-nova-interacao">+ registrar interação</button>';
    }
    var self = this;
    var opcoesTipo = Object.keys(ROTULOS_TIPO_INTERACAO).filter(function (t) { return t !== "xp" && t !== "loot"; }).map(function (t) {
      return '<option value="' + t + '"' + (t === ni.tipo ? " selected" : "") + ">" + ROTULOS_TIPO_INTERACAO[t] + "</option>";
    }).join("");
    var pendentes = ni.participantesPendentes.map(function (p, idx) {
      return (
        '<li>' + escapeHtml(p.nome) + " — " +
        '<select data-acao="papel-pendente" data-indice="' + idx + '">' +
        Object.keys(ROTULOS_PAPEL).map(function (pp) {
          return '<option value="' + pp + '"' + (pp === p.papel ? " selected" : "") + ">" + ROTULOS_PAPEL[pp] + "</option>";
        }).join("") + "</select> " +
        '<button type="button" class="botao-remover" data-acao="remover-pendente" data-indice="' + idx + '">×</button>' +
        "</li>"
      );
    }).join("");
    var opcoesTipoAtor = TIPOS_ATOR.map(function (t) {
      return '<option value="' + t + '"' + (t === ni.busca.tipo ? " selected" : "") + ">" + ROTULOS_TIPO_ATOR[t] + "</option>";
    }).join("");
    var resultadosBusca = (ni.busca.resultados || []).map(function (p) {
      return p.fichas.map(function (f) {
        var rotulo = f.is_base ? p.nome : p.nome + " (" + f.rotulo + ")";
        return (
          "<tr><td>" + escapeHtml(rotulo) + "</td>" +
          '<td><button type="button" class="botao-secundario" data-acao="adicionar-pendente" data-ficha="' + f.id + '" data-nome="' + escapeHtml(rotulo) + '">adicionar</button></td></tr>'
        );
      }).join("");
    }).join("");
    return (
      '<div class="sessao-viva__form-interacao">' +
      '<select data-acao="interacao-tipo">' + opcoesTipo + "</select>" +
      '<input type="text" class="input-medio" placeholder="Descrição (opcional)" value="' + escapeHtml(ni.descricao) + '" data-acao="interacao-descricao">' +
      '<input type="text" class="input-medio" placeholder="Perícia/atributo (opcional)" value="' + escapeHtml(ni.periciaOuAtributo) + '" data-acao="interacao-pericia">' +
      '<input type="number" class="input-pequeno" placeholder="CD" value="' + escapeHtml(ni.cd) + '" data-acao="interacao-cd">' +
      '<select data-acao="interacao-sucesso">' +
      '<option value=""' + (ni.sucesso === "" ? " selected" : "") + ">—</option>" +
      '<option value="1"' + (ni.sucesso === "1" ? " selected" : "") + ">Sucesso</option>" +
      '<option value="0"' + (ni.sucesso === "0" ? " selected" : "") + ">Falha</option>" +
      "</select>" +
      '<div class="sessao-viva__form-rolagem">' +
      '<input type="text" class="input-pequeno" placeholder="Dado (ex.: 1d20+5)" value="' + escapeHtml(ni.dado) + '" data-acao="interacao-dado">' +
      '<select data-acao="interacao-vantagem">' +
      '<option value=""' + (!ni.vantagem ? " selected" : "") + ">Normal</option>" +
      '<option value="vantagem"' + (ni.vantagem === "vantagem" ? " selected" : "") + ">Vantagem</option>" +
      '<option value="desvantagem"' + (ni.vantagem === "desvantagem" ? " selected" : "") + ">Desvantagem</option>" +
      "</select>" +
      '<button type="button" class="botao-secundario" data-acao="rolar-online">🎲 Rolar online</button>' +
      '<input type="number" class="input-pequeno" placeholder="Resultado" value="' + escapeHtml(ni.resultadoTotal) + '" data-acao="interacao-resultado">' +
      "</div>" +
      "<p><strong>Participantes:</strong></p>" +
      '<ul class="sessao-viva__pendentes">' + (pendentes || '<li class="ajuda">Nenhum ainda.</li>') + "</ul>" +
      '<div class="combate-painel__busca-topo">' +
      '<select data-acao="busca-interacao-tipo">' + opcoesTipoAtor + "</select>" +
      '<input type="search" placeholder="Buscar por nome…" value="' + escapeHtml(ni.busca.q || "") + '" data-acao="busca-interacao-q">' +
      "</div>" +
      (resultadosBusca
        ? '<table class="ficha-personagem__picker-tabela"><tbody>' + resultadosBusca + "</tbody></table>"
        : "") +
      '<div class="sessao-viva__acoes">' +
      '<button type="button" class="botao-principal" data-acao="salvar-interacao">Registrar</button> ' +
      '<button type="button" class="botao-secundario" data-acao="cancelar-interacao">Cancelar</button>' +
      "</div></div>"
    );
  };

  // ------------------------------------------------------------------------
  // Eventos
  // ------------------------------------------------------------------------

  Widget.prototype._buscarAtor = function () {
    var self = this;
    var b = this.novaInteracao.busca;
    fetch("/api/personagens-busca?tipo=" + encodeURIComponent(b.tipo) + "&q=" + encodeURIComponent(b.q || ""))
      .then(function (r) { return r.json(); })
      .then(function (d) { b.resultados = d.itens || []; self.renderizar(); });
  };

  Widget.prototype.ligarEventos = function () {
    var self = this;

    this.raiz.addEventListener("input", function (ev) {
      var alvo = ev.target;
      var acao = alvo.getAttribute("data-acao");
      if (!acao) return;
      if (self.editandoTempo && acao.indexOf("tempo-") === 0) {
        self.editandoTempo[acao.slice(6)] = alvo.value;
      } else if (self.novoLugar && acao === "novo-lugar-nome") {
        self.novoLugar.nome = alvo.value;
      } else if (self.novaInteracao) {
        var mapa = {
          "interacao-descricao": "descricao", "interacao-pericia": "periciaOuAtributo",
          "interacao-cd": "cd", "interacao-dado": "dado", "interacao-resultado": "resultadoTotal",
        };
        if (mapa[acao]) { self.novaInteracao[mapa[acao]] = alvo.value; }
        else if (acao === "busca-interacao-q") { self.novaInteracao.busca.q = alvo.value; self._buscarAtor(); }
      }
    });

    this.raiz.addEventListener("change", function (ev) {
      var alvo = ev.target;
      var acao = alvo.getAttribute("data-acao");
      if (!acao) return;
      if (acao === "escolher-lugar") {
        self.chamar("PUT", self._url("/lugar"), { lugar_id: alvo.value ? parseInt(alvo.value, 10) : null })
          .then(function (dados) { if (dados) { self.sessaoViva = dados.sessao_viva; self.renderizar(); } });
      } else if (acao === "novo-lugar-pai") {
        self.novoLugar.lugarPaiId = alvo.value;
      } else if (self.novaInteracao) {
        if (acao === "interacao-tipo") self.novaInteracao.tipo = alvo.value;
        else if (acao === "interacao-sucesso") self.novaInteracao.sucesso = alvo.value;
        else if (acao === "interacao-vantagem") self.novaInteracao.vantagem = alvo.value;
        else if (acao === "busca-interacao-tipo") { self.novaInteracao.busca.tipo = alvo.value; self._buscarAtor(); }
        else if (acao === "papel-pendente") {
          var idx = parseInt(alvo.getAttribute("data-indice"), 10);
          self.novaInteracao.participantesPendentes[idx].papel = alvo.value;
        }
      }
    });

    this.raiz.addEventListener("click", function (ev) {
      var botao = ev.target.closest("button[data-acao]");
      if (!botao) return;
      var acao = botao.getAttribute("data-acao");

      if (acao === "editar-tempo") {
        var v = self.sessaoViva || {};
        self.editandoTempo = { ano: v.ano || "", mes: v.mes || "", dia: v.dia || "", hora: v.hora || "", minuto: v.minuto || "" };
        self.renderizar();
      } else if (acao === "cancelar-tempo") {
        self.editandoTempo = null;
        self.renderizar();
      } else if (acao === "salvar-tempo") {
        var t = self.editandoTempo;
        self.chamar("PUT", self._url("/tempo"), { ano: t.ano, mes: t.mes, dia: t.dia, hora: t.hora, minuto: t.minuto })
          .then(function (dados) { if (dados) { self.editandoTempo = null; self.sessaoViva = dados.sessao_viva; self.renderizar(); } });
      } else if (acao === "avancar-tempo") {
        self.chamar("PUT", self._url("/tempo"), { minutos: parseInt(botao.getAttribute("data-minutos"), 10) })
          .then(function (dados) { if (dados) { self.sessaoViva = dados.sessao_viva; self.renderizar(); } });
      } else if (acao === "descanso-curto" || acao === "descanso-longo") {
        self.chamar("PUT", self._url("/tempo"), { minutos: acao === "descanso-curto" ? 60 : 480 })
          .then(function (dados) { if (dados) { self.sessaoViva = dados.sessao_viva; self.renderizar(); } });
      } else if (acao === "abrir-novo-lugar") {
        self.novoLugar = { nome: "", lugarPaiId: "" };
        self.renderizar();
      } else if (acao === "cancelar-novo-lugar") {
        self.novoLugar = null;
        self.renderizar();
      } else if (acao === "salvar-novo-lugar") {
        if (!self.novoLugar.nome.trim()) return;
        self.chamar("POST", self._url("/lugares-provisorio"), {
          nome: self.novoLugar.nome, lugar_pai_id: self.novoLugar.lugarPaiId ? parseInt(self.novoLugar.lugarPaiId, 10) : null,
        }).then(function (dados) {
          if (!dados) return;
          self.novoLugar = null;
          self.chamar("PUT", self._url("/lugar"), { lugar_id: dados.lugar.id }).then(function () { self.carregar(); });
        });
      } else if (acao === "abrir-nova-interacao") {
        self.novaInteracao = {
          tipo: "evento_livre", descricao: "", periciaOuAtributo: "", cd: "", sucesso: "",
          dado: "", vantagem: "", resultadoBruto: null, resultadoTotal: "", online: false,
          participantesPendentes: [], busca: { tipo: "jogador", q: "", resultados: [] },
        };
        self.renderizar();
      } else if (acao === "cancelar-interacao") {
        self.novaInteracao = null;
        self.renderizar();
      } else if (acao === "rolar-online") {
        var ni = self.novaInteracao;
        if (!ni.dado.trim()) { window.alert("Informe a fórmula do dado (ex.: 1d20+5)."); return; }
        self.chamar("POST", "/api/rolar", { dado: ni.dado, vantagem: ni.vantagem || null }).then(function (res) {
          if (!res) return;
          ni.resultadoBruto = res.resultado_bruto;
          ni.resultadoTotal = String(res.resultado_total);
          ni.online = true;
          self.renderizar();
        });
      } else if (acao === "adicionar-pendente") {
        self.novaInteracao.participantesPendentes.push({
          fichaId: parseInt(botao.getAttribute("data-ficha"), 10), nome: botao.getAttribute("data-nome"), papel: "ator",
        });
        self.renderizar();
      } else if (acao === "remover-pendente") {
        self.novaInteracao.participantesPendentes.splice(parseInt(botao.getAttribute("data-indice"), 10), 1);
        self.renderizar();
      } else if (acao === "salvar-interacao") {
        var n = self.novaInteracao;
        var corpo = {
          tipo: n.tipo, descricao: n.descricao, pericia_ou_atributo: n.periciaOuAtributo,
          cd: n.cd === "" ? null : parseInt(n.cd, 10),
          sucesso: n.sucesso === "" ? null : n.sucesso === "1",
          participantes: n.participantesPendentes.map(function (p) { return { ficha_id: p.fichaId, papel: p.papel }; }),
          rolagens: n.dado.trim()
            ? [{ dado: n.dado, vantagem: n.vantagem || null, resultado_bruto: n.resultadoBruto, resultado_total: n.resultadoTotal === "" ? null : parseInt(n.resultadoTotal, 10), online: n.online }]
            : [],
        };
        self.chamar("POST", self._url("/interacoes"), corpo).then(function (dados) {
          if (!dados) return;
          self.novaInteracao = null;
          self.carregar();
        });
      }
    });
  };

  function iniciar() {
    document.querySelectorAll(".sessao-viva-painel[data-pagina]").forEach(function (raiz) {
      new Widget(raiz);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
