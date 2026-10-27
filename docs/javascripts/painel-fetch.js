/* Infra compartilhada para widgets embutidos direto nas páginas do site que falam com o Painel
 * do Mestre local (Flask, admin/app.py) por fetch(), sem redirecionar para outra aba/origem.
 * Usado por gallancourt.js (formulários de NPC/Lugar/Jogador) e, mais adiante, pelo criador de
 * sessão embutido. painel-iniciativa.js tem seu próprio Widget, mais específico (re-renderiza o
 * estado inteiro a cada chamada) — continua como está, sem usar este arquivo.
 *
 * Precisa carregar ANTES de gallancourt.js em mkdocs.yml (extra_javascript).
 */
window.GallancourtPainel = (function () {
  "use strict";

  function escapeHtml(valor) {
    return String(valor == null ? "" : valor)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function base(elemento) {
    return (elemento.getAttribute("data-painel-url") || "http://127.0.0.1:5001").replace(/\/$/, "");
  }

  function tratarResposta(r) {
    return r.json().then(function (dados) {
      if (!r.ok || dados.erro) throw new Error(dados.erro || ("HTTP " + r.status));
      return dados;
    });
  }

  // JSON no corpo (GET sem corpo, ou POST/PUT com um objeto).
  function chamarJSON(baseUrl, caminho, metodo, corpo) {
    var opcoes = { method: metodo || "GET" };
    if (corpo !== undefined) {
      opcoes.headers = { "Content-Type": "application/json" };
      opcoes.body = JSON.stringify(corpo);
    }
    return fetch(baseUrl + caminho, opcoes).then(tratarResposta);
  }

  // multipart/form-data — usado pelos formulários de criar NPC/Lugar/Jogador (o de NPC pode
  // incluir um arquivo de imagem; o fetch cuida do Content-Type/boundary sozinho com FormData).
  function chamarFormData(baseUrl, caminho, formData) {
    return fetch(baseUrl + caminho, { method: "POST", body: formData }).then(tratarResposta);
  }

  function erroHtml(baseUrl, erro) {
    return '<p class="painel-erro">⚠️ Não consegui falar com o Painel do Mestre em ' +
      "<code>" + escapeHtml(baseUrl) + "</code>. Confirme que ele está rodando no seu " +
      "computador (<code>admin\\iniciar-painel.bat</code>) e tente de novo. " +
      "<small>(" + escapeHtml(erro && erro.message) + ")</small></p>";
  }

  return {
    escapeHtml: escapeHtml, base: base, chamarJSON: chamarJSON, chamarFormData: chamarFormData,
    erroHtml: erroHtml,
  };
})();
