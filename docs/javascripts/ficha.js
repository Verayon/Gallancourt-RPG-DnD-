/* Ficha de personagem embutida (ver admin/personagens_api.py e hooks/gallancourt.py::
 * _ficha_dinamica_personagem) — widget que roda dentro da `<div class="ficha-personagem"
 * data-tipo data-slug>` de cada página de monstro/NPC/jogador, falando por fetch() com a API do
 * banco (admin/app.py, rotas /api/personagens/... e /api/catalogo/...). Sem framework, mesmo
 * esqueleto de painel-iniciativa.js: busca ao carregar, redesenha a cada ação a partir da
 * resposta. Sucessor de monstro-ficha.js (2026-10-30) — agora cobre monstro/NPC nomeado/jogador
 * com o mesmo widget, ver .claude/contexto/personagens.md.
 *
 * Em modo leitura (sem Modo Mestre), mostra só o cartão. Em Modo Mestre: CR (monstro) ou Nível/
 * XP/Classe/Antecedente (npc/jogador), CA/PV máximo/PV temporário/Deslocamento/Percepção passiva/
 * Iniciativa extra/Dados de vida editáveis direto nos chips do topo; atributos com modificador
 * calculado ao digitar; uma segunda faixa de abas (Atributos/Inventário/Grimório/
 * Características/Efeitos/Biografia/Diário) organiza o resto: equipamento/habilidades/magias/
 * idiomas/sentidos/perícias com botão de remover e um seletor "+ adicionar" (tabela completa do
 * catálogo, busca sem perder o foco); sentidos/perícias têm valor próprio editável direto na
 * lista; Inventário ganha moeda (5 campos) e carga máxima; Grimório ganha pools de espaço de
 * magia; Efeitos ganha uma grade de condições (15 fixas) e uma lista de efeitos aplicados;
 * Biografia/Diário editam o Personagem (não a Ficha) — persistem num PUT separado; foto do
 * personagem (uma por Personagem, compartilhada entre Base e variantes).
 */
(function () {
  "use strict";

  var ROTULOS_ATRIBUTOS = { for: "FOR", des: "DES", con: "CON", int: "INT", sab: "SAB", car: "CAR" };
  var ORDEM_ATRIBUTOS = ["for", "des", "con", "int", "sab", "car"];
  var CAMPO_PARA_COLUNA_ATRIBUTO = { for: "forca", des: "destreza", con: "constituicao", int: "inteligencia", sab: "sabedoria", car: "carisma" };
  var ROTULOS_TIPO_HABILIDADE_PLURAL = { traco: "Traços", acao: "Ações", reacao: "Reações" };

  // Mesma tabela de CR->XP do SRD usada no servidor (admin/personagens_api.py::CR_PARA_XP) — só
  // pra mostrar o XP ao lado da lista suspensa sem precisar ida e volta ao servidor.
  var CR_OPCOES = [
    "0", "1/8", "1/4", "1/2", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24",
    "25", "26", "27", "28", "29", "30",
  ];
  var CR_PARA_XP = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100, "1": 200, "2": 450, "3": 700, "4": 1100,
    "5": 1800, "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900, "11": 7200, "12": 8400,
    "13": 10000, "14": 11500, "15": 13000, "16": 15000, "17": 18000, "18": 20000, "19": 22000,
    "20": 25000, "21": 33000, "22": 41000, "23": 50000, "24": 62000, "25": 75000, "26": 90000,
    "27": 105000, "28": 120000, "29": 135000, "30": 155000,
  };

  // Mesma lista fixa do servidor (admin/banco.py::CONDICOES_D20) — as 15 condições do 5e.
  var CONDICOES_D20 = [
    "Agarrado", "Apavorado", "Atordoado", "Caído", "Cego", "Enfeitiçado", "Envenenado",
    "Exausto", "Incapacitado", "Inconsciente", "Invisível", "Paralisado", "Petrificado",
    "Restringido", "Surdo",
  ];
  var TIPOS_EFEITO = ["Temporário", "Passivo", "Inativo"];

  // Mesma lista fixa do servidor (admin/banco.py::TIPOS_DANO) — os 13 tipos de dano do 5e.
  var TIPOS_DANO = [
    "Ácido", "Contundente", "Cortante", "Elétrico", "Fogo", "Força", "Frio", "Necrótico",
    "Perfurante", "Psíquico", "Radiante", "Sônico", "Veneno",
  ];
  var MODOS_RESISTENCIA_DANO = [["imune", "Imune"], ["resistente", "Resistente"], ["vulneravel", "Vulnerável"]];

  // Colunas extras (além de Nome) mostradas na tabela do seletor "+ adicionar", por tipo —
  // mesmas informações da página de cada catálogo (itens/magias), não só o nome.
  var COLUNAS_PICKER = {
    equipamentos: [["categoria", "Categoria"], ["custo", "Custo"], ["dano_formula", "Dano"], ["dano_tipo", "Tipo"], ["propriedades", "Propriedades"]],
    magias: [["nivel", "Nível"], ["escola", "Escola"], ["tempo", "Tempo"], ["alcance", "Alcance"], ["componentes", "Comp."], ["duracao", "Duração"]],
    habilidades: [["tipo", "Tipo"], ["bonus_acerto", "Bônus"], ["dano_formula", "Dano"], ["dano_tipo", "Tipo de dano"]],
    idiomas: [],
    sentidos: [],
    pericias: [["atributo", "Atributo"], ["fonte", "Fonte"]],
  };
  var CAMPOS_NOVO_CATALOGO = {
    equipamentos: [["nome", "Nome", "text"], ["categoria", "Categoria", "text"], ["dano_formula", "Dano (ex.: 1d6+2)", "text"],
      ["dano_tipo", "Tipo de dano", "text"], ["ca_bonus", "Bônus de CA", "number"], ["peso_kg", "Peso (kg)", "number"], ["descricao", "Descrição", "text"]],
    habilidades: [["nome", "Nome", "text"], ["tipo", "Tipo (traco/acao/reacao)", "text"], ["bonus_acerto", "Bônus de acerto", "number"],
      ["dano_formula", "Dano (ex.: 1d6+2)", "text"], ["dano_tipo", "Tipo de dano", "text"], ["descricao", "Descrição", "text"]],
    magias: [["nome", "Nome", "text"], ["nivel", "Nível", "number"], ["escola", "Escola", "text"], ["descricao", "Descrição", "text"]],
    idiomas: [["nome", "Nome", "text"]],
    sentidos: [["nome", "Nome", "text"]],
    pericias: [["nome", "Nome", "text"], ["atributo", "Atributo", "text"], ["fonte", "Fonte", "text"]],
  };
  var TITULOS_GRUPO = {
    equipamentos: "equipamento", habilidades: "traço/ação/reação", magias: "magia",
    idiomas: "idioma", sentidos: "sentido", pericias: "perícia",
  };

  var ABAS_CONTEUDO = [
    ["atributos", "Atributos"], ["inventario", "Inventário"], ["grimorio", "Grimório"],
    ["caracteristicas", "Características"], ["efeitos", "Efeitos"],
    ["biografia", "Biografia"], ["diario", "Diário"],
  ];

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

  function assinado(valor) {
    var n = parseInt(valor, 10);
    return isNaN(n) ? "" : (n >= 0 ? "+" + n : String(n));
  }

  function arredondarPasso(valor) {
    // Evita resíduo de ponto flutuante (9 - 1.5 - 1.5 = 5.999999999999999).
    return Math.round(valor * 100) / 100;
  }

  function Widget(raiz) {
    this.raiz = raiz;
    this.tipo = raiz.getAttribute("data-tipo");
    this.slug = raiz.getAttribute("data-slug");
    this.dados = null;
    this.autenticado = false;
    this.abaAtiva = 0;
    this.abaConteudo = "atributos";
    this.pickerAberto = null; // {tipo, busca, resultados}
    this._buscaTimer = null;
    this.ligarEventos();
    this.carregar();
  }

  Widget.prototype._base = function () {
    return "/api/personagens/" + this.tipo + "/" + this.slug;
  };

  Widget.prototype.carregar = function () {
    var self = this;
    Promise.all([
      fetch(this._base()).then(function (r) { return r.json(); }),
      fetch("/api/auth/estado").then(function (r) { return r.json(); }).catch(function () { return { autenticado: false }; }),
    ]).then(function (resultados) {
      if (resultados[0].erro) {
        self.raiz.innerHTML = '<p class="ajuda">Ficha ainda não cadastrada no banco.</p>';
        return;
      }
      self.dados = resultados[0];
      self.autenticado = !!resultados[1].autenticado;
      if (self.abaAtiva >= self.dados.fichas.length) self.abaAtiva = 0;
      self.renderizar();
    }).catch(function (erro) {
      self.raiz.innerHTML = '<p class="painel-iniciativa__erro">⚠️ Não consegui falar com o Painel do Mestre. ' +
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
    return fetch(caminho, opcoes).then(function (r) { return r.json().then(function (d) { return { ok: r.ok, dados: d }; }); })
      .then(function (res) {
        if (!res.ok || res.dados.erro) { window.alert(res.dados.erro || "Não deu certo."); return false; }
        self.dados = res.dados;
        if (self.abaAtiva >= self.dados.fichas.length) self.abaAtiva = Math.max(0, self.dados.fichas.length - 1);
        self.pickerAberto = null;
        self.renderizar();
        return true;
      })
      .catch(function (erro) { window.alert("Erro: " + erro.message); return false; });
  };

  // --------------------------------------------------------------------
  // Montagem do HTML
  // --------------------------------------------------------------------

  Widget.prototype.renderizar = function () {
    var self = this;
    var d = this.dados;
    var abasFicha = d.fichas.map(function (f, i) {
      return '<button type="button" class="ficha-personagem__aba' + (i === self.abaAtiva ? " ficha-personagem__aba--ativa" : "") +
        '" data-acao="trocar-aba" data-indice="' + i + '">' + escapeHtml(f.rotulo) + "</button>";
    }).join("");
    var botaoNova = this.autenticado
      ? '<button type="button" class="ficha-personagem__aba ficha-personagem__aba--nova" data-acao="nova-variante" title="Criar variante a partir da ficha atual">+</button>'
      : "";

    var ficha = d.fichas[this.abaAtiva];
    var abasConteudo = ABAS_CONTEUDO.map(function (par) {
      return '<button type="button" class="ficha-personagem__aba2' + (par[0] === self.abaConteudo ? " ficha-personagem__aba2--ativa" : "") +
        '" data-acao="trocar-aba2" data-aba2="' + par[0] + '">' + par[1] + "</button>";
    }).join("");

    this.raiz.innerHTML =
      this._foto() +
      '<div class="ficha-personagem__abas">' + abasFicha + botaoNova + "</div>" +
      (ficha ? this._cartao(ficha) : '<p class="ajuda">Nenhuma ficha ainda.</p>') +
      (ficha ? '<div class="ficha-personagem__abas2">' + abasConteudo + "</div>" + this._conteudoAba(ficha) : "") +
      (ficha && this.autenticado ? this._rodape(ficha) : "");
  };

  Widget.prototype._foto = function () {
    var d = this.dados;
    if (!this.autenticado) {
      return d.foto ? '<img class="ficha-personagem__foto" src="' + escapeHtml(d.foto) + '" alt="' + escapeHtml(d.nome) + '">' : "";
    }
    if (d.foto) {
      return (
        '<div class="ficha-personagem__foto-bloco">' +
        '<img class="ficha-personagem__foto" src="' + escapeHtml(d.foto) + '" alt="' + escapeHtml(d.nome) + '">' +
        '<button type="button" class="botao-remover" data-acao="apagar-foto" title="Remover foto">× remover foto</button>' +
        "</div>"
      );
    }
    return (
      '<div class="ficha-personagem__foto-bloco">' +
      '<label class="botao-secundario ficha-personagem__foto-upload">+ adicionar foto' +
      '<input type="file" accept="image/*" data-acao="enviar-foto" hidden></label>' +
      "</div>"
    );
  };

  Widget.prototype._chipTexto = function (rotulo, valor) {
    return '<span><strong>' + escapeHtml(rotulo) + "</strong> " + escapeHtml(valor) + "</span>";
  };

  Widget.prototype._chipsEdicao = function (f) {
    var partes = [];
    if (this.tipo === "monstro") {
      var opcoesCr = CR_OPCOES.map(function (v) {
        return '<option value="' + v + '"' + (v === (f.cr || "") ? " selected" : "") + ">" + v + "</option>";
      }).join("");
      var xp = f.cr_xp != null ? f.cr_xp.toLocaleString("pt-BR") + " PE" : "";
      partes.push(
        '<span class="chip-editavel"><strong>CR</strong>' +
        '<select data-campo="cr">' + opcoesCr + "</select>" +
        '<span class="ajuda" data-cr-xp>' + escapeHtml(xp) + "</span></span>"
      );
    } else {
      partes.push(
        '<span class="chip-editavel"><strong>Nível</strong>' +
        '<input type="number" min="1" class="input-pequeno" data-campo="nivel" value="' + (f.nivel != null ? f.nivel : "") + '"></span>' +
        '<span class="chip-editavel"><strong>XP</strong>' +
        '<input type="number" min="0" class="input-medio" data-campo="xp" value="' + (f.xp != null ? f.xp : "") + '"></span>' +
        '<span class="chip-editavel"><strong>Classe</strong>' +
        '<input type="text" class="input-medio" data-campo="classe" value="' + escapeHtml(f.classe || "") + '"></span>' +
        '<span class="chip-editavel"><strong>Subclasse</strong>' +
        '<input type="text" class="input-medio" data-campo="subclasse" value="' + escapeHtml(f.subclasse || "") + '"></span>' +
        '<span class="chip-editavel"><strong>Antecedente</strong>' +
        '<input type="text" class="input-medio" data-campo="antecedente" value="' + escapeHtml(f.antecedente || "") + '"></span>'
      );
    }
    partes.push(
      '<span class="chip-editavel"><strong>CA</strong>' +
      '<button type="button" class="chip-passo" data-campo="ca_total" data-passo="-1">−</button>' +
      '<input type="number" min="0" data-campo="ca_total" value="' + f.ca_total + '">' +
      '<button type="button" class="chip-passo" data-campo="ca_total" data-passo="1">+</button></span>' +

      '<span class="chip-editavel"><strong>PV máximo</strong>' +
      '<button type="button" class="chip-passo" data-campo="pv_maximo" data-passo="-1">−</button>' +
      '<input type="number" min="1" data-campo="pv_maximo" value="' + f.pv_maximo + '">' +
      '<button type="button" class="chip-passo" data-campo="pv_maximo" data-passo="1">+</button></span>' +

      '<span class="chip-editavel"><strong>PV temporário</strong>' +
      '<button type="button" class="chip-passo" data-campo="pv_temporario" data-passo="-1">−</button>' +
      '<input type="number" min="0" data-campo="pv_temporario" value="' + f.pv_temporario + '">' +
      '<button type="button" class="chip-passo" data-campo="pv_temporario" data-passo="1">+</button></span>' +

      '<span class="chip-editavel"><strong>Dados de vida</strong>' +
      '<input type="text" class="input-pequeno" placeholder="ex.: 3d8" data-campo="dados_vida_total" value="' + escapeHtml(f.dados_vida_total || "") + '">' +
      '<span>usados</span>' +
      '<input type="number" min="0" class="input-pequeno" data-campo="dados_vida_usados" value="' + f.dados_vida_usados + '"></span>' +

      '<span class="chip-editavel"><strong>Deslocamento</strong>' +
      '<button type="button" class="chip-passo" data-campo="deslocamento_m" data-passo="-1.5">−</button>' +
      '<input type="number" min="0" step="1.5" data-campo="deslocamento_m" value="' + f.deslocamento_m + '">' +
      "<span>m</span>" +
      '<button type="button" class="chip-passo" data-campo="deslocamento_m" data-passo="1.5">+</button></span>' +

      '<span class="chip-editavel"><strong>Outros desloc.</strong>' +
      '<input type="text" class="input-medio" placeholder="ex.: voo 18 m" data-campo="deslocamento_extra" value="' +
      escapeHtml(f.deslocamento_extra || "") + '"></span>' +

      '<span class="chip-editavel"><strong>Percepção passiva</strong>' +
      '<button type="button" class="chip-passo" data-campo="percepcao_passiva" data-passo="-1">−</button>' +
      '<input type="number" min="0" data-campo="percepcao_passiva" value="' + f.percepcao_passiva + '">' +
      '<button type="button" class="chip-passo" data-campo="percepcao_passiva" data-passo="1">+</button></span>' +

      '<span class="chip-editavel"><strong>Investigação passiva</strong>' +
      '<button type="button" class="chip-passo" data-campo="investigacao_passiva" data-passo="-1">−</button>' +
      '<input type="number" min="0" data-campo="investigacao_passiva" value="' + f.investigacao_passiva + '">' +
      '<button type="button" class="chip-passo" data-campo="investigacao_passiva" data-passo="1">+</button></span>' +

      '<span class="chip-editavel"><strong>Intuição passiva</strong>' +
      '<button type="button" class="chip-passo" data-campo="intuicao_passiva" data-passo="-1">−</button>' +
      '<input type="number" min="0" data-campo="intuicao_passiva" value="' + f.intuicao_passiva + '">' +
      '<button type="button" class="chip-passo" data-campo="intuicao_passiva" data-passo="1">+</button></span>' +

      '<span class="chip-editavel"><strong>Iniciativa extra</strong>' +
      '<button type="button" class="chip-passo" data-campo="iniciativa_extra" data-passo="-1">−</button>' +
      '<input type="number" data-campo="iniciativa_extra" value="' + f.iniciativa_extra + '">' +
      '<button type="button" class="chip-passo" data-campo="iniciativa_extra" data-passo="1">+</button></span>'
    );
    return partes.join("");
  };

  Widget.prototype._chipsLeitura = function (f) {
    var desloc = f.deslocamento_m + " m" + (f.deslocamento_extra ? ", " + f.deslocamento_extra : "");
    var xp = f.cr_xp != null ? " (" + f.cr_xp.toLocaleString("pt-BR") + " PE)" : "";
    var partes = [];
    if (this.tipo === "monstro") {
      if (f.cr) partes.push(this._chipTexto("CR", f.cr + xp));
    } else {
      if (f.nivel != null) partes.push(this._chipTexto("Nível", f.nivel));
      if (f.classe) partes.push(this._chipTexto("Classe", f.classe + (f.subclasse ? " (" + f.subclasse + ")" : "")));
      if (f.antecedente) partes.push(this._chipTexto("Antecedente", f.antecedente));
    }
    partes.push(this._chipTexto("CA", f.ca_total));
    var pv = (f.pv_atual != null ? f.pv_atual : "—") + "/" + (f.pv_maximo != null ? f.pv_maximo : "—");
    if (f.pv_temporario) pv += " (+" + f.pv_temporario + " temp.)";
    partes.push(this._chipTexto("PV", pv));
    partes.push(this._chipTexto("Deslocamento", desloc));
    partes.push(this._chipTexto("Percepção passiva", f.percepcao_passiva));
    partes.push(this._chipTexto("Investigação passiva", f.investigacao_passiva));
    partes.push(this._chipTexto("Intuição passiva", f.intuicao_passiva));
    return partes.join("");
  };

  Widget.prototype._cartao = function (f) {
    var editavel = this.autenticado;
    return (
      '<div class="stat-block" data-ficha-id="' + f.id + '">' +
      '<div class="stat-block__topo"><div class="stat-block__chips">' +
      (editavel ? this._chipsEdicao(f) : this._chipsLeitura(f)) +
      "</div></div></div>"
    );
  };

  Widget.prototype._atributosGrid = function (f, editavel) {
    var atributos = ORDEM_ATRIBUTOS.map(function (a) {
      var info = f.atributos[a];
      if (editavel) {
        return '<div class="ficha-personagem__atributo"><label>' + ROTULOS_ATRIBUTOS[a] +
          '<input type="number" min="1" data-campo-atributo="' + a + '" value="' + info.valor + '"></label>' +
          '<span class="ficha-personagem__modificador" data-mod-de="' + a + '">(' + info.modificador + ")</span></div>";
      }
      return '<div class="ficha-personagem__atributo"><strong>' + ROTULOS_ATRIBUTOS[a] + "</strong> " +
        info.valor + " (" + info.modificador + ")</div>";
    }).join("");
    return '<div class="ficha-personagem__atributos">' + atributos + "</div>";
  };

  Widget.prototype._conteudoAba = function (f) {
    var editavel = this.autenticado;
    switch (this.abaConteudo) {
      case "inventario":
        return this._abaInventario(f, editavel);
      case "grimorio":
        return this._abaGrimorio(f, editavel);
      case "caracteristicas":
        return this._abaCaracteristicas(f, editavel);
      case "efeitos":
        return this._abaEfeitos(f, editavel);
      case "biografia":
        return this._abaBiografia(editavel);
      case "diario":
        return this._abaDiario(editavel);
      default:
        return this._abaAtributos(f, editavel);
    }
  };

  Widget.prototype._abaAtributos = function (f, editavel) {
    return (
      '<div class="ficha-personagem__painel-aba">' +
      this._atributosGrid(f, editavel) +
      this._listaPericias(f, editavel) +
      this._listaIdiomas(f, editavel) + this._listaSentidos(f, editavel) +
      this._listaResistenciasDano(f, editavel) +
      "</div>"
    );
  };

  Widget.prototype._listaResistenciasDano = function (f, editavel) {
    var ativos = {};
    (f.resistencias_dano || []).forEach(function (r) { ativos[r.nome] = r; });
    if (!editavel) {
      var pilulas = TIPOS_DANO.filter(function (t) { return ativos[t]; }).map(function (t) {
        var rotuloModo = MODOS_RESISTENCIA_DANO.filter(function (m) { return m[0] === ativos[t].modo; })[0][1];
        return '<span class="pilula pilula--ativa">' + escapeHtml(t) + " (" + rotuloModo + ")</span>";
      }).join("");
      return pilulas
        ? '<div class="ficha-personagem__grupo"><p><strong>Resistências a dano</strong></p>' +
          '<div class="ficha-personagem__condicoes">' + pilulas + "</div></div>"
        : "";
    }
    var linhas = TIPOS_DANO.map(function (tipo) {
      var ativo = ativos[tipo];
      var botoes = MODOS_RESISTENCIA_DANO.map(function (m) {
        var ligado = ativo && ativo.modo === m[0];
        return '<button type="button" class="pilula' + (ligado ? " pilula--ativa" : "") + '" ' +
          'data-acao="alternar-resistencia-dano" data-nome="' + escapeHtml(tipo) + '" data-modo="' + m[0] + '">' +
          m[1] + "</button>";
      }).join("");
      return '<div class="ficha-personagem__resistencia-linha"><span>' + escapeHtml(tipo) + "</span>" + botoes + "</div>";
    }).join("");
    return (
      '<div class="ficha-personagem__grupo"><p><strong>Imunidades / Resistências / Vulnerabilidades a dano</strong></p>' +
      linhas + "</div>"
    );
  };

  Widget.prototype._abaInventario = function (f, editavel) {
    var moedas = ["pc", "pp", "pe", "po", "pl"].map(function (sigla) {
      var campo = "moeda_" + sigla;
      return editavel
        ? '<label class="ficha-personagem__moeda">' + sigla.toUpperCase() +
          '<input type="number" min="0" class="input-pequeno" data-campo="' + campo + '" value="' + f[campo] + '"></label>'
        : '<span class="pilula">' + sigla.toUpperCase() + " " + f[campo] + "</span>";
    }).join("");
    var carga = editavel
      ? '<label class="ficha-personagem__moeda">Carga máx. (kg)' +
        '<input type="number" min="0" class="input-pequeno" data-campo="carga_maxima" value="' + (f.carga_maxima != null ? f.carga_maxima : "") + '" placeholder="padrão SRD"></label>'
      : (f.carga_maxima != null ? this._chipTexto("Carga máxima", f.carga_maxima + " kg") : "");
    var pesoTotal = (f.equipamentos || []).reduce(function (soma, e) {
      return soma + (e.peso_kg || 0) * (e.quantidade || 1);
    }, 0);
    var cargaMaxima = f.carga_maxima != null ? f.carga_maxima : f.atributos.for.valor * 2;
    var estourou = pesoTotal > cargaMaxima;
    var resumoCarga = '<span class="ficha-personagem__carga-total' + (estourou ? " ficha-personagem__carga-total--estourada" : "") + '">' +
      "Carga atual: " + arredondarPasso(pesoTotal) + "/" + arredondarPasso(cargaMaxima) + " kg" +
      (estourou ? " — sobrecarregado!" : "") + "</span>";
    return (
      '<div class="ficha-personagem__painel-aba">' +
      resumoCarga +
      this._listaCatalogo(f, editavel, "equipamentos", f.equipamentos) +
      '<div class="ficha-personagem__grupo"><p><strong>Moeda e carga</strong></p>' +
      '<div class="ficha-personagem__moedas">' + moedas + carga + "</div></div>" +
      "</div>"
    );
  };

  Widget.prototype._cabecalhoGrimorio = function (f, editavel) {
    if (editavel) {
      return (
        '<div class="ficha-personagem__grupo">' +
        '<span class="chip-editavel"><strong>CD de conjuração</strong>' +
        '<button type="button" class="chip-passo" data-campo="cd_conjuracao" data-passo="-1">−</button>' +
        '<input type="number" min="0" data-campo="cd_conjuracao" value="' + (f.cd_conjuracao != null ? f.cd_conjuracao : "") + '">' +
        '<button type="button" class="chip-passo" data-campo="cd_conjuracao" data-passo="1">+</button></span>' +
        '<span class="chip-editavel"><strong>Bônus de ataque mágico</strong>' +
        '<button type="button" class="chip-passo" data-campo="bonus_ataque_magico" data-passo="-1">−</button>' +
        '<input type="number" data-campo="bonus_ataque_magico" value="' + (f.bonus_ataque_magico != null ? f.bonus_ataque_magico : "") + '">' +
        '<button type="button" class="chip-passo" data-campo="bonus_ataque_magico" data-passo="1">+</button></span>' +
        "</div>"
      );
    }
    var partes = [];
    if (f.cd_conjuracao != null) partes.push(this._chipTexto("CD de conjuração", f.cd_conjuracao));
    if (f.bonus_ataque_magico != null) partes.push(this._chipTexto("Bônus de ataque mágico", assinado(f.bonus_ataque_magico)));
    return partes.length ? '<div class="ficha-personagem__grupo stat-block__chips">' + partes.join("") + "</div>" : "";
  };

  Widget.prototype._abaGrimorio = function (f, editavel) {
    return (
      '<div class="ficha-personagem__painel-aba">' +
      this._cabecalhoGrimorio(f, editavel) +
      this._listaCatalogo(f, editavel, "magias", f.magias) +
      this._listaEspacosMagia(f, editavel) +
      "</div>"
    );
  };

  Widget.prototype._abaCaracteristicas = function (f, editavel) {
    return '<div class="ficha-personagem__painel-aba">' + this._listaHabilidades(f, editavel) + "</div>";
  };

  Widget.prototype._abaEfeitos = function (f, editavel) {
    return (
      '<div class="ficha-personagem__painel-aba">' +
      this._listaCondicoes(f, editavel) +
      this._listaEfeitos(f, editavel) +
      "</div>"
    );
  };

  Widget.prototype._campoBiografia = function (chave, rotulo, valor, area) {
    var editavel = this.autenticado;
    if (!editavel) return valor ? "<p><strong>" + escapeHtml(rotulo) + ":</strong> " + escapeHtml(valor) + "</p>" : "";
    var campo = area
      ? '<textarea rows="3" data-campo-personagem="' + chave + '">' + escapeHtml(valor || "") + "</textarea>"
      : '<input type="text" data-campo-personagem="' + chave + '" value="' + escapeHtml(valor || "") + '">';
    return '<label class="ficha-personagem__campo-bio">' + rotulo + campo + "</label>";
  };

  Widget.prototype._abaBiografia = function (editavel) {
    var p = this.dados;
    var fisicos = [
      ["genero", "Gênero"], ["idade", "Idade"], ["altura", "Altura"], ["peso_corporal", "Peso"],
      ["olhos", "Olhos"], ["cabelo", "Cabelo"], ["pele", "Pele"], ["fe", "Fé"],
    ].map(function (c) { return this._campoBiografia(c[0], c[1], p[c[0]], false); }, this).join("");
    var textos = [
      ["aparencia", "Aparência"], ["personalidade", "Personalidade"], ["traco", "Traço marcante"],
      ["ideal", "Ideal"], ["vinculo", "Vínculo"], ["defeito", "Defeito"],
      ["pessoas_interesse", "Pessoas de interesse"], ["lugares_interesse", "Lugares de interesse"],
    ].map(function (c) { return this._campoBiografia(c[0], c[1], p[c[0]], true); }, this).join("");
    return (
      '<div class="ficha-personagem__painel-aba">' +
      '<div class="ficha-personagem__bio-fisicos">' + fisicos + "</div>" +
      '<div class="ficha-personagem__bio-textos">' + textos + "</div>" +
      "</div>"
    );
  };

  Widget.prototype._abaDiario = function (editavel) {
    var entradas = (this.dados.diario || []).map(function (e) {
      var remover = editavel
        ? '<button type="button" class="botao-remover" data-acao="remover-diario" data-vinculo="' + e.id + '" title="Remover">×</button>'
        : "";
      return (
        '<div class="ficha-personagem__diario-entrada">' +
        '<div class="ficha-personagem__diario-cabeca"><strong>' + escapeHtml(e.titulo || "(sem título)") + "</strong>" +
        (e.data ? ' <span class="ajuda">' + escapeHtml(e.data) + "</span>" : "") + remover + "</div>" +
        (e.texto ? "<p>" + escapeHtml(e.texto) + "</p>" : "") +
        "</div>"
      );
    }).join("");
    var formulario = editavel
      ? (
        '<div class="ficha-personagem__diario-novo">' +
        '<input type="text" class="input-pequeno" placeholder="Data" data-novo-diario="data">' +
        '<input type="text" placeholder="Título" data-novo-diario="titulo">' +
        '<textarea rows="3" placeholder="O que aconteceu…" data-novo-diario="texto"></textarea>' +
        '<button type="button" class="botao-principal" data-acao="nova-entrada-diario">+ nova entrada</button>' +
        "</div>"
      )
      : "";
    return (
      '<div class="ficha-personagem__painel-aba">' + formulario +
      (entradas || '<p class="ajuda">Nenhuma entrada ainda.</p>') + "</div>"
    );
  };

  Widget.prototype._listaIdiomas = function (f, editavel) {
    var linhas = f.idiomas.map(function (i) {
      var remover = editavel
        ? ' <button type="button" class="botao-remover" data-acao="remover-vinculo" data-tipo="idiomas" data-vinculo="' + i.vinculo_id + '" title="Remover">×</button>'
        : "";
      return "<li>" + escapeHtml(i.nome) + remover + "</li>";
    }).join("");
    if (!linhas && !editavel) return "";
    var botaoAdicionar = editavel
      ? '<button type="button" class="botao-secundario ficha-personagem__adicionar" data-acao="abrir-picker" data-tipo="idiomas">+ adicionar idioma</button>'
      : "";
    return (
      '<div class="ficha-personagem__grupo"><p><strong>Idiomas</strong></p>' +
      (linhas ? '<ul class="ficha-personagem__lista-simples">' + linhas + "</ul>" : "") +
      botaoAdicionar + this._pickerSeAberto("idiomas") + "</div>"
    );
  };

  Widget.prototype._listaSentidos = function (f, editavel) {
    var linhas = f.sentidos.map(function (s) {
      if (editavel) {
        return (
          "<li>" + escapeHtml(s.nome) + " " +
          '<input type="number" min="0" class="input-pequeno" data-sentido-valor data-vinculo="' + s.vinculo_id + '" value="' + (s.valor != null ? s.valor : "") + '" placeholder="m">' +
          " m" +
          ' <button type="button" class="botao-remover" data-acao="remover-vinculo" data-tipo="sentidos" data-vinculo="' + s.vinculo_id + '" title="Remover">×</button></li>'
        );
      }
      return "<li><strong>" + escapeHtml(s.nome) + "</strong>" + (s.valor != null ? " " + s.valor + " m" : "") + "</li>";
    }).join("");
    if (!linhas && !editavel) return "";
    var botaoAdicionar = editavel
      ? '<button type="button" class="botao-secundario ficha-personagem__adicionar" data-acao="abrir-picker" data-tipo="sentidos">+ adicionar sentido</button>'
      : "";
    return (
      '<div class="ficha-personagem__grupo"><p><strong>Sentidos</strong></p>' +
      (linhas ? '<ul class="ficha-personagem__lista-simples">' + linhas + "</ul>" : "") +
      botaoAdicionar + this._pickerSeAberto("sentidos") + "</div>"
    );
  };

  Widget.prototype._listaPericias = function (f, editavel) {
    var linhas = f.pericias.map(function (p) {
      if (editavel) {
        return (
          "<li>" + escapeHtml(p.nome) + " " +
          '<input type="number" class="input-pequeno" data-pericia-bonus data-vinculo="' + p.vinculo_id + '" value="' + p.bonus + '" placeholder="bônus">' +
          ' <button type="button" class="botao-remover" data-acao="remover-vinculo" data-tipo="pericias" data-vinculo="' + p.vinculo_id + '" title="Remover">×</button></li>'
        );
      }
      return "<li><strong>" + escapeHtml(p.nome) + "</strong> " + (p.bonus >= 0 ? "+" : "") + p.bonus + "</li>";
    }).join("");
    if (!linhas && !editavel) return "";
    var botaoAdicionar = editavel
      ? '<button type="button" class="botao-secundario ficha-personagem__adicionar" data-acao="abrir-picker" data-tipo="pericias">+ adicionar perícia</button>'
      : "";
    return (
      '<div class="ficha-personagem__grupo"><p><strong>Perícias</strong></p>' +
      (linhas ? '<ul class="ficha-personagem__lista-simples">' + linhas + "</ul>" : "") +
      botaoAdicionar + this._pickerSeAberto("pericias") + "</div>"
    );
  };

  Widget.prototype._listaCatalogo = function (f, editavel, tipo, itens) {
    if (!itens.length && !editavel) return "";
    var linhas = itens.map(function (e) {
      var remover = editavel
        ? ' <button type="button" class="botao-remover" data-acao="remover-vinculo" data-tipo="' + tipo + '" data-vinculo="' + e.vinculo_id + '" title="Remover">×</button>'
        : "";
      var detalhe = [];
      if (tipo === "equipamentos") {
        detalhe = [e.categoria, e.ca_bonus ? "CA +" + e.ca_bonus : e.ca_formula, e.dano_formula ? (e.dano_formula + " " + (e.dano_tipo || "")) : null, e.peso_kg != null ? e.peso_kg + " kg" : null];
      } else if (tipo === "magias") {
        detalhe = [e.nivel != null ? "nível " + e.nivel : null, e.escola, e.alcance];
      }
      detalhe = detalhe.filter(Boolean).join(" · ");
      var favorito = "";
      if (tipo === "magias") {
        favorito = editavel
          ? '<button type="button" class="botao-favorito' + (e.favorito ? " botao-favorito--ativo" : "") +
            '" data-acao="alternar-favorito" data-tipo="magias" data-vinculo="' + e.vinculo_id + '" title="Favoritar">★</button> '
          : (e.favorito ? "★ " : "");
      }
      return "<li>" + favorito + "<strong>" + escapeHtml(e.nome) + "</strong>" + (detalhe ? " — " + escapeHtml(detalhe) : "") + remover + "</li>";
    }).join("");
    var titulo = tipo === "equipamentos" ? "Equipamento" : "Magias";
    var botaoAdicionar = editavel
      ? '<button type="button" class="botao-secundario ficha-personagem__adicionar" data-acao="abrir-picker" data-tipo="' + tipo + '">+ adicionar ' + TITULOS_GRUPO[tipo] + "</button>"
      : "";
    return (
      '<div class="ficha-personagem__grupo"><p><strong>' + titulo + "</strong></p>" +
      (linhas ? "<ul>" + linhas + "</ul>" : "") + botaoAdicionar + this._pickerSeAberto(tipo) + "</div>"
    );
  };

  Widget.prototype._listaHabilidades = function (f, editavel) {
    var grupos = { traco: [], acao: [], reacao: [] };
    f.habilidades.forEach(function (h) { (grupos[h.tipo] || grupos.traco).push(h); });
    var corpo = "";
    ["traco", "acao", "reacao"].forEach(function (tipo) {
      if (!grupos[tipo].length) return;
      corpo += "<p><strong>" + ROTULOS_TIPO_HABILIDADE_PLURAL[tipo] + "</strong></p><ul>";
      grupos[tipo].forEach(function (h) {
        var sufixo = [];
        if (h.bonus_acerto != null) sufixo.push((h.bonus_acerto >= 0 ? "+" : "") + h.bonus_acerto + " para acertar");
        if (h.dano_formula) sufixo.push(h.dano_formula + (h.dano_tipo ? " " + h.dano_tipo : ""));
        var favorito = editavel
          ? '<button type="button" class="botao-favorito' + (h.favorito ? " botao-favorito--ativo" : "") +
            '" data-acao="alternar-favorito" data-tipo="habilidades" data-vinculo="' + h.vinculo_id + '" title="Favoritar">★</button> '
          : (h.favorito ? "★ " : "");
        var usos = "";
        if (editavel) {
          usos = ' <span class="ajuda">usos/descanso ' +
            '<input type="number" min="0" class="input-pequeno" data-habilidade-usos-maximo data-vinculo="' + h.vinculo_id + '" value="' + (h.usos_maximo != null ? h.usos_maximo : "") + '" placeholder="—">' +
            '<select data-habilidade-tipo-descanso data-vinculo="' + h.vinculo_id + '">' +
            '<option value="">(nenhum)</option>' +
            ["curto", "longo"].map(function (t) { return '<option value="' + t + '"' + (h.tipo_descanso === t ? " selected" : "") + ">" + t + "</option>"; }).join("") +
            "</select></span>";
          if (h.usos_maximo != null) {
            usos += ' <button type="button" class="botao-secundario" data-acao="usar-habilidade" data-vinculo="' + h.vinculo_id + '"' +
              (h.usos_restantes <= 0 ? " disabled" : "") + ">usar (" + h.usos_restantes + "/" + h.usos_maximo + ")</button>";
          }
        } else if (h.usos_maximo != null) {
          usos = ' <span class="ajuda">(' + h.usos_restantes + "/" + h.usos_maximo + " usos)</span>";
        }
        var remover = editavel
          ? ' <button type="button" class="botao-remover" data-acao="remover-vinculo" data-tipo="habilidades" data-vinculo="' + h.vinculo_id + '" title="Remover">×</button>'
          : "";
        corpo += "<li>" + favorito + "<strong>" + escapeHtml(h.nome) + ".</strong> " + escapeHtml(h.descricao || "") +
          (sufixo.length ? ' <span class="ajuda">(' + escapeHtml(sufixo.join(", ")) + ")</span>" : "") + usos + remover + "</li>";
      });
      corpo += "</ul>";
    });
    var botaoAdicionar = editavel
      ? '<button type="button" class="botao-secundario ficha-personagem__adicionar" data-acao="abrir-picker" data-tipo="habilidades">+ adicionar traço/ação/reação</button>'
      : "";
    return '<div class="ficha-personagem__grupo">' + corpo + botaoAdicionar + this._pickerSeAberto("habilidades") + "</div>";
  };

  Widget.prototype._listaEspacosMagia = function (f, editavel) {
    var linhas = (f.espacos_magia || []).map(function (e) {
      if (editavel) {
        return (
          '<li class="ficha-personagem__espaco-magia">' +
          '<input type="text" class="input-pequeno" placeholder="rótulo" data-espaco-campo="rotulo" data-vinculo="' + e.vinculo_id + '" value="' + escapeHtml(e.rotulo || "") + '">' +
          '<label>nível <input type="number" min="1" class="input-pequeno" data-espaco-campo="nivel" data-vinculo="' + e.vinculo_id + '" value="' + e.nivel + '"></label>' +
          '<label>usados <input type="number" min="0" class="input-pequeno" data-espaco-campo="usado" data-vinculo="' + e.vinculo_id + '" value="' + e.usado + '"></label>' +
          '<label>de <input type="number" min="0" class="input-pequeno" data-espaco-campo="maximo" data-vinculo="' + e.vinculo_id + '" value="' + e.maximo + '"></label>' +
          '<button type="button" class="botao-remover" data-acao="remover-espaco-magia" data-vinculo="' + e.vinculo_id + '" title="Remover">×</button>' +
          "</li>"
        );
      }
      return "<li>" + (e.rotulo ? escapeHtml(e.rotulo) + " — " : "") + "Nível " + e.nivel + ": " + e.usado + "/" + e.maximo + "</li>";
    }).join("");
    var botaoAdicionar = editavel
      ? '<button type="button" class="botao-secundario ficha-personagem__adicionar" data-acao="novo-espaco-magia">+ adicionar pool de espaços</button>'
      : "";
    if (!linhas && !editavel) return "";
    return (
      '<div class="ficha-personagem__grupo"><p><strong>Espaços de magia</strong></p>' +
      (linhas ? '<ul class="ficha-personagem__lista-simples">' + linhas + "</ul>" : "") +
      botaoAdicionar + "</div>"
    );
  };

  Widget.prototype._listaCondicoes = function (f, editavel) {
    var ativas = {};
    (f.condicoes || []).forEach(function (c) { ativas[c.nome] = c.vinculo_id; });
    var pilulas = CONDICOES_D20.map(function (nome) {
      var ativa = ativas[nome] != null;
      if (!editavel) {
        return ativa ? '<span class="pilula pilula--ativa">' + nome + "</span>" : "";
      }
      return (
        '<button type="button" class="pilula' + (ativa ? " pilula--ativa" : "") + '" ' +
        'data-acao="alternar-condicao" data-nome="' + escapeHtml(nome) + '" data-vinculo="' + (ativa ? ativas[nome] : "") + '">' +
        nome + "</button>"
      );
    }).join("");
    return '<div class="ficha-personagem__grupo"><p><strong>Condições</strong></p><div class="ficha-personagem__condicoes">' + pilulas + "</div></div>";
  };

  Widget.prototype._listaEfeitos = function (f, editavel) {
    var linhas = (f.efeitos || []).map(function (e) {
      if (editavel) {
        return (
          '<li class="ficha-personagem__efeito">' +
          '<input type="text" placeholder="Nome" data-efeito-campo="nome" data-vinculo="' + e.vinculo_id + '" value="' + escapeHtml(e.nome) + '">' +
          '<select data-efeito-campo="tipo" data-vinculo="' + e.vinculo_id + '">' +
          TIPOS_EFEITO.map(function (t) { return '<option value="' + t + '"' + (t === e.tipo ? " selected" : "") + ">" + t + "</option>"; }).join("") +
          "</select>" +
          '<input type="text" class="input-medio" placeholder="Origem" data-efeito-campo="origem" data-vinculo="' + e.vinculo_id + '" value="' + escapeHtml(e.origem || "") + '">' +
          '<input type="text" class="input-pequeno" placeholder="Duração" data-efeito-campo="duracao" data-vinculo="' + e.vinculo_id + '" value="' + escapeHtml(e.duracao || "") + '">' +
          '<button type="button" class="botao-remover" data-acao="remover-efeito" data-vinculo="' + e.vinculo_id + '" title="Remover">×</button>' +
          "</li>"
        );
      }
      return "<li><strong>" + escapeHtml(e.nome) + "</strong> (" + escapeHtml(e.tipo) + ")" +
        (e.origem ? " — " + escapeHtml(e.origem) : "") + (e.duracao ? ", " + escapeHtml(e.duracao) : "") + "</li>";
    }).join("");
    var formulario = editavel
      ? (
        '<div class="ficha-personagem__efeito-novo">' +
        '<input type="text" placeholder="Nome do efeito" data-novo-efeito="nome">' +
        '<select data-novo-efeito="tipo">' + TIPOS_EFEITO.map(function (t) { return "<option>" + t + "</option>"; }).join("") + "</select>" +
        '<input type="text" class="input-medio" placeholder="Origem" data-novo-efeito="origem">' +
        '<input type="text" class="input-pequeno" placeholder="Duração" data-novo-efeito="duracao">' +
        '<button type="button" class="botao-principal" data-acao="novo-efeito">+ adicionar efeito</button>' +
        "</div>"
      )
      : "";
    return (
      '<div class="ficha-personagem__grupo"><p><strong>Efeitos aplicados</strong></p>' + formulario +
      (linhas ? '<ul class="ficha-personagem__lista-simples ficha-personagem__lista-simples--coluna">' + linhas + "</ul>" : (editavel ? "" : '<p class="ajuda">Nenhum.</p>')) +
      "</div>"
    );
  };

  Widget.prototype._pickerSeAberto = function (tipo) {
    return this.pickerAberto && this.pickerAberto.tipo === tipo ? this._picker(tipo) : "";
  };

  Widget.prototype._picker = function (tipo) {
    return (
      '<div class="ficha-personagem__picker">' +
      '<div class="ficha-personagem__picker-topo">' +
      '<input type="search" placeholder="Buscar ' + TITULOS_GRUPO[tipo] + '…" data-acao="buscar-picker" data-tipo="' + tipo + '" value="' + escapeHtml(this.pickerAberto.busca || "") + '" autofocus>' +
      '<button type="button" class="botao-remover ficha-personagem__picker-fechar" data-acao="fechar-picker" title="Fechar">× Fechar</button>' +
      "</div>" +
      '<div data-picker-resultados>' + this._pickerResultadosHtml(tipo) + "</div>" +
      '<details class="ficha-personagem__picker-novo"><summary>Criar entrada nova no catálogo</summary>' +
      '<div class="ficha-personagem__picker-novo-campos">' +
      CAMPOS_NOVO_CATALOGO[tipo].map(function (c) {
        return '<label>' + c[1] + '<input type="' + c[2] + '"' + (c[2] === "number" ? ' min="0"' : "") + ' data-novo-campo="' + c[0] + '"></label>';
      }).join("") +
      "</div>" +
      '<button type="button" class="botao-principal" data-acao="criar-e-usar" data-tipo="' + tipo + '">Criar e usar</button>' +
      "</details>" +
      "</div>"
    );
  };

  Widget.prototype._pickerResultadosHtml = function (tipo) {
    var resultados = this.pickerAberto.resultados || [];
    if (!resultados.length) return '<p class="ajuda">Nada encontrado — crie uma entrada nova abaixo.</p>';
    var colunas = COLUNAS_PICKER[tipo];
    var cabecalho = "<tr><th>Nome</th>" + colunas.map(function (c) { return "<th>" + c[1] + "</th>"; }).join("") + "<th></th></tr>";
    var linhas = resultados.map(function (item) {
      var celulas = colunas.map(function (c) { return "<td>" + escapeHtml(item[c[0]]) + "</td>"; }).join("");
      return "<tr><td>" + escapeHtml(item.nome) + "</td>" + celulas +
        '<td><button type="button" class="botao-secundario" data-acao="usar-picker" data-tipo="' + tipo + '" data-item="' + item.id + '">usar</button></td></tr>';
    }).join("");
    return '<table class="ficha-personagem__picker-tabela"><thead>' + cabecalho + "</thead><tbody>" + linhas + "</tbody></table>";
  };

  Widget.prototype._rodape = function (f) {
    return (
      '<div class="ficha-personagem__acoes-rodape">' +
      '<button type="button" class="botao-principal" data-acao="salvar-ficha" data-ficha="' + f.id + '">Salvar</button>' +
      (this.tipo !== "monstro"
        ? '<button type="button" class="botao-secundario" data-acao="descanso-curto" data-ficha="' + f.id +
          '" title="Repõe os usos de habilidade marcados como descanso curto">Descanso curto</button>' +
          '<button type="button" class="botao-secundario" data-acao="descanso-longo" data-ficha="' + f.id +
          '" title="PV volta ao máximo, espaços de magia zeram, dados de vida recuperam pela metade">Descanso longo</button>'
        : "") +
      (f.is_base ? "" : '<button type="button" class="botao-remover" data-acao="excluir-ficha" data-ficha="' + f.id + '">Excluir esta ficha</button>') +
      "</div>"
    );
  };

  // --------------------------------------------------------------------
  // Eventos
  // --------------------------------------------------------------------

  Widget.prototype.fichaAtual = function () {
    return this.dados.fichas[this.abaAtiva];
  };

  Widget.prototype.buscarCatalogo = function (tipo, busca) {
    var self = this;
    this.pickerAberto = this.pickerAberto && this.pickerAberto.tipo === tipo
      ? Object.assign({}, this.pickerAberto, { busca: busca })
      : { tipo: tipo, busca: busca, resultados: [] };
    fetch("/api/catalogo/" + tipo + "?busca=" + encodeURIComponent(busca || ""))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!self.pickerAberto || self.pickerAberto.tipo !== tipo) return; // fechou enquanto buscava
        self.pickerAberto.resultados = d.itens || [];
        // Atualiza só os resultados — nunca o <input> de busca, pra não perder o foco/cursor
        // no meio da digitação (era o bug: redesenhar o widget inteiro recriava o campo).
        var alvo = self.raiz.querySelector("[data-picker-resultados]");
        if (alvo) alvo.innerHTML = self._pickerResultadosHtml(tipo);
      });
  };

  Widget.prototype.ligarEventos = function () {
    var self = this;

    this.raiz.addEventListener("input", function (ev) {
      var alvo = ev.target;
      if (alvo.matches && alvo.matches("[data-campo-atributo]")) {
        var span = self.raiz.querySelector('[data-mod-de="' + alvo.getAttribute("data-campo-atributo") + '"]');
        if (span) span.textContent = "(" + modificador(alvo.value) + ")";
      }
      if (alvo.matches && alvo.matches('[data-acao="buscar-picker"]')) {
        var tipo = alvo.getAttribute("data-tipo"), valor = alvo.value;
        window.clearTimeout(self._buscaTimer);
        self._buscaTimer = window.setTimeout(function () { self.buscarCatalogo(tipo, valor); }, 250);
      }
    });

    this.raiz.addEventListener("change", function (ev) {
      if (ev.target.matches && ev.target.matches('[data-campo="cr"]')) {
        var xpSpan = self.raiz.querySelector("[data-cr-xp]");
        var xp = CR_PARA_XP[ev.target.value];
        if (xpSpan) xpSpan.textContent = xp != null ? xp.toLocaleString("pt-BR") + " PE" : "";
      }
      if (ev.target.matches && ev.target.matches('[data-acao="enviar-foto"]')) {
        self.enviarFoto(ev.target.files && ev.target.files[0]);
      }
      var ficha = self.fichaAtual();
      if (ev.target.matches && ev.target.matches("[data-habilidade-usos-maximo]")) {
        var valor = ev.target.value;
        self.chamar("PUT", "/api/fichas/" + ficha.id + "/habilidades/" + ev.target.getAttribute("data-vinculo") + "/usos",
          { usos_maximo: valor === "" ? null : valor });
      }
      if (ev.target.matches && ev.target.matches("[data-habilidade-tipo-descanso]")) {
        self.chamar("PUT", "/api/fichas/" + ficha.id + "/habilidades/" + ev.target.getAttribute("data-vinculo") + "/usos",
          { tipo_descanso: ev.target.value || null });
      }
    });

    this.raiz.addEventListener("click", function (ev) {
      var passo = ev.target.closest("button.chip-passo");
      if (passo) {
        var input = self.raiz.querySelector('input[data-campo="' + passo.getAttribute("data-campo") + '"]');
        if (input) {
          var min = input.hasAttribute("min") ? parseFloat(input.min) : -Infinity;
          var novo = arredondarPasso(parseFloat(input.value || "0") + parseFloat(passo.getAttribute("data-passo")));
          input.value = Math.max(min, novo);
        }
        return;
      }

      var botao = ev.target.closest("button[data-acao]");
      if (!botao) return;
      var acao = botao.getAttribute("data-acao");
      var ficha = self.fichaAtual();

      if (acao === "trocar-aba") {
        self.abaAtiva = parseInt(botao.getAttribute("data-indice"), 10) || 0;
        self.pickerAberto = null;
        self.renderizar();
      } else if (acao === "trocar-aba2") {
        self.abaConteudo = botao.getAttribute("data-aba2");
        self.pickerAberto = null;
        self.renderizar();
      } else if (acao === "nova-variante") {
        var rotulo = window.prompt("Nome curto da variante (ex.: Arqueiro):", "");
        if (rotulo === null) return;
        self.chamar("POST", self._base() + "/fichas", { rotulo: rotulo }).then(function (ok) {
          if (ok) { self.abaAtiva = self.dados.fichas.length - 1; self.renderizar(); }
        });
      } else if (acao === "excluir-ficha") {
        if (!window.confirm("Excluir esta ficha? Não dá pra desfazer.")) return;
        self.chamar("DELETE", self._base() + "/fichas/" + botao.getAttribute("data-ficha"));
      } else if (acao === "descanso-curto") {
        if (!window.confirm("Aplicar um descanso curto? Repõe os usos de habilidade marcados como descanso curto.")) return;
        self.chamar("POST", self._base() + "/fichas/" + botao.getAttribute("data-ficha") + "/descanso-curto");
      } else if (acao === "descanso-longo") {
        if (!window.confirm("Aplicar um descanso longo? PV volta ao máximo, espaços de magia zeram e dados de vida recuperam pela metade.")) return;
        self.chamar("POST", self._base() + "/fichas/" + botao.getAttribute("data-ficha") + "/descanso-longo");
      } else if (acao === "salvar-ficha") {
        self.salvarFicha(botao.getAttribute("data-ficha"));
      } else if (acao === "remover-vinculo") {
        self.chamar("DELETE", "/api/fichas/" + ficha.id + "/" + botao.getAttribute("data-tipo") + "/" + botao.getAttribute("data-vinculo"));
      } else if (acao === "abrir-picker") {
        self.buscarCatalogo(botao.getAttribute("data-tipo"), "");
        self.renderizar();
      } else if (acao === "fechar-picker") {
        self.pickerAberto = null;
        self.renderizar();
      } else if (acao === "usar-picker") {
        self.chamar("POST", "/api/fichas/" + ficha.id + "/" + botao.getAttribute("data-tipo"), { item_id: botao.getAttribute("data-item") });
      } else if (acao === "criar-e-usar") {
        self.criarEUsar(botao.getAttribute("data-tipo"), botao.closest(".ficha-personagem__picker"));
      } else if (acao === "apagar-foto") {
        if (!window.confirm("Remover a foto deste personagem?")) return;
        self.chamar("DELETE", self._base() + "/foto");
      } else if (acao === "novo-espaco-magia") {
        self.chamar("POST", "/api/fichas/" + ficha.id + "/espacos-magia", { nivel: 1, maximo: 1, usado: 0 });
      } else if (acao === "remover-espaco-magia") {
        self.chamar("DELETE", "/api/fichas/" + ficha.id + "/espacos-magia/" + botao.getAttribute("data-vinculo"));
      } else if (acao === "alternar-condicao") {
        var vinculo = botao.getAttribute("data-vinculo");
        if (vinculo) {
          self.chamar("DELETE", "/api/fichas/" + ficha.id + "/condicoes/" + vinculo);
        } else {
          self.chamar("POST", "/api/fichas/" + ficha.id + "/condicoes", { nome: botao.getAttribute("data-nome") });
        }
      } else if (acao === "alternar-resistencia-dano") {
        self.chamar("POST", "/api/fichas/" + ficha.id + "/resistencias-dano", {
          nome: botao.getAttribute("data-nome"), modo: botao.getAttribute("data-modo"),
        });
      } else if (acao === "alternar-favorito") {
        self.chamar("PUT", "/api/fichas/" + ficha.id + "/" + botao.getAttribute("data-tipo") + "/" + botao.getAttribute("data-vinculo") + "/favorito");
      } else if (acao === "usar-habilidade") {
        self.chamar("POST", "/api/fichas/" + ficha.id + "/habilidades/" + botao.getAttribute("data-vinculo") + "/usar");
      } else if (acao === "novo-efeito") {
        self.novoEfeito(ficha, botao.closest(".ficha-personagem__efeito-novo"));
      } else if (acao === "remover-efeito") {
        self.chamar("DELETE", "/api/fichas/" + ficha.id + "/efeitos/" + botao.getAttribute("data-vinculo"));
      } else if (acao === "nova-entrada-diario") {
        self.novaEntradaDiario(botao.closest(".ficha-personagem__diario-novo"));
      } else if (acao === "remover-diario") {
        self.chamar("DELETE", self._base() + "/diario/" + botao.getAttribute("data-vinculo"));
      }
    });
  };

  Widget.prototype.salvarFicha = function (fichaId) {
    var self = this;
    var campos = {};
    this.raiz.querySelectorAll("[data-campo]").forEach(function (el) {
      campos[el.getAttribute("data-campo")] = el.value;
    });
    this.raiz.querySelectorAll("[data-campo-atributo]").forEach(function (el) {
      campos[CAMPO_PARA_COLUNA_ATRIBUTO[el.getAttribute("data-campo-atributo")]] = el.value;
    });
    var sentidosAlterados = [];
    this.raiz.querySelectorAll("[data-sentido-valor]").forEach(function (el) {
      sentidosAlterados.push({ vinculo: el.getAttribute("data-vinculo"), valor: el.value });
    });
    var periciasAlteradas = [];
    this.raiz.querySelectorAll("[data-pericia-bonus]").forEach(function (el) {
      periciasAlteradas.push({ vinculo: el.getAttribute("data-vinculo"), bonus: el.value });
    });
    var espacosAlterados = {};
    this.raiz.querySelectorAll("[data-espaco-campo]").forEach(function (el) {
      var v = el.getAttribute("data-vinculo");
      espacosAlterados[v] = espacosAlterados[v] || {};
      espacosAlterados[v][el.getAttribute("data-espaco-campo")] = el.value;
    });
    var efeitosAlterados = {};
    this.raiz.querySelectorAll("[data-efeito-campo]").forEach(function (el) {
      var v = el.getAttribute("data-vinculo");
      efeitosAlterados[v] = efeitosAlterados[v] || {};
      efeitosAlterados[v][el.getAttribute("data-efeito-campo")] = el.value;
    });
    var camposPersonagem = {};
    var temCamposPersonagem = false;
    this.raiz.querySelectorAll("[data-campo-personagem]").forEach(function (el) {
      camposPersonagem[el.getAttribute("data-campo-personagem")] = el.value;
      temCamposPersonagem = true;
    });

    var pendentes = [];
    sentidosAlterados.forEach(function (s) {
      pendentes.push(fetch("/api/fichas/" + fichaId + "/sentidos/" + s.vinculo, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ valor: s.valor }),
      }));
    });
    periciasAlteradas.forEach(function (p) {
      pendentes.push(fetch("/api/fichas/" + fichaId + "/pericias/" + p.vinculo, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ bonus: p.bonus }),
      }));
    });
    Object.keys(espacosAlterados).forEach(function (vinculo) {
      pendentes.push(fetch("/api/fichas/" + fichaId + "/espacos-magia/" + vinculo, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(espacosAlterados[vinculo]),
      }));
    });
    Object.keys(efeitosAlterados).forEach(function (vinculo) {
      pendentes.push(fetch("/api/fichas/" + fichaId + "/efeitos/" + vinculo, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(efeitosAlterados[vinculo]),
      }));
    });
    if (temCamposPersonagem) {
      pendentes.push(fetch(this._base(), {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(camposPersonagem),
      }));
    }

    this.chamar("PUT", this._base() + "/fichas/" + fichaId, campos).then(function (ok) {
      if (!ok || !pendentes.length) return;
      Promise.all(pendentes).then(function () { self.carregar(); });
    });
  };

  Widget.prototype.criarEUsar = function (tipo, painelPicker) {
    var self = this;
    var campos = {};
    painelPicker.querySelectorAll("[data-novo-campo]").forEach(function (el) {
      if (el.value) campos[el.getAttribute("data-novo-campo")] = el.value;
    });
    if (!campos.nome) { window.alert("Dê um nome."); return; }
    fetch("/api/catalogo/" + tipo, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(campos) })
      .then(function (r) { return r.json(); })
      .then(function (item) {
        if (item.erro) { window.alert(item.erro); return; }
        var ficha = self.fichaAtual();
        self.chamar("POST", "/api/fichas/" + ficha.id + "/" + tipo, { item_id: item.id });
      });
  };

  Widget.prototype.novoEfeito = function (ficha, painel) {
    var campos = {};
    painel.querySelectorAll("[data-novo-efeito]").forEach(function (el) {
      if (el.value) campos[el.getAttribute("data-novo-efeito")] = el.value;
    });
    if (!campos.nome) { window.alert("Dê um nome ao efeito."); return; }
    this.chamar("POST", "/api/fichas/" + ficha.id + "/efeitos", campos);
  };

  Widget.prototype.novaEntradaDiario = function (painel) {
    var campos = {};
    painel.querySelectorAll("[data-novo-diario]").forEach(function (el) {
      if (el.value) campos[el.getAttribute("data-novo-diario")] = el.value;
    });
    if (!campos.titulo && !campos.texto) { window.alert("Escreva ao menos um título ou texto."); return; }
    this.chamar("POST", this._base() + "/diario", campos);
  };

  Widget.prototype.enviarFoto = function (arquivo) {
    if (!arquivo) return;
    var self = this;
    var dados = new FormData();
    dados.append("foto", arquivo);
    fetch(this._base() + "/foto", { method: "POST", body: dados })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.erro) { window.alert(d.erro); return; }
        self.dados = d;
        self.renderizar();
      });
  };

  function iniciar() {
    document.querySelectorAll(".ficha-personagem[data-slug]").forEach(function (raiz) {
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
