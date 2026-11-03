/* Popup público de "Reportar bug" (botão flutuante injetado por hooks/gallancourt.py::
 * _rodape_global, presente em toda página — ver docs/stylesheets/extra.css .botao-reportar-bug).
 * Mesmo padrão do popup de login do Modo Mestre (docs/javascripts/modo-mestre.js): sem navegar
 * pra outra página, sem precisar de senha — qualquer um pode reportar. Fala com /api/bugs/opcoes
 * (GET) e /api/bugs (POST), ambas públicas mesmo com PAINEL_SENHA definida (ver _ROTAS_LIVRES em
 * admin/app.py). A página atual (location.pathname) vai sozinha no envio; a versão do site é
 * preenchida no servidor a partir do changelog, não pelo navegador.
 */
(function () {
  "use strict";

  function escapeHtml(valor) {
    return String(valor == null ? "" : valor)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function opcoes(lista) {
    return lista.map(function (v) {
      return '<option value="' + escapeHtml(v) + '">' + escapeHtml(v) + "</option>";
    }).join("");
  }

  function abrirPopup() {
    if (document.getElementById("bug-report-popup")) return;
    var popup = document.createElement("div");
    popup.id = "bug-report-popup";
    popup.className = "modo-mestre-popup";
    popup.innerHTML =
      '<div class="modo-mestre-popup__caixa">' +
      '<button type="button" class="botao-remover modo-mestre-popup__fechar" data-acao="fechar">× Fechar</button>' +
      "<h3>🐞 Reportar um problema</h3>" +
      '<p class="modo-mestre-popup__ajuda">Página: <code>' + escapeHtml(location.pathname) + "</code></p>" +
      '<form class="bug-report-form" data-acao="enviar">' +
      '<label>Tipo de problema<select name="tipo" required><option value="">Carregando…</option></select></label>' +
      '<label>O que está errado?<textarea name="descricao" rows="4" placeholder="O que você esperava, o que aconteceu e como repetir." required></textarea></label>' +
      '<button type="submit" class="botao-principal">Enviar</button>' +
      "</form>" +
      '<p class="modo-mestre-popup__erro" hidden></p>' +
      '<p class="modo-mestre-popup__sucesso" hidden></p>' +
      "</div>";
    document.body.appendChild(popup);

    fetch("/api/bugs/opcoes")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var select = popup.querySelector('select[name="tipo"]');
        if (select) select.innerHTML = opcoes(d.tipos || []);
      })
      .catch(function () {
        var select = popup.querySelector('select[name="tipo"]');
        if (select) select.innerHTML = '<option value="Outro">Outro</option>';
      });

    function fechar() { popup.remove(); }

    popup.addEventListener("click", function (ev) {
      if (ev.target === popup || ev.target.closest('[data-acao="fechar"]')) fechar();
    });

    popup.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var dados = new FormData(ev.target);
      var erro = popup.querySelector(".modo-mestre-popup__erro");
      var sucesso = popup.querySelector(".modo-mestre-popup__sucesso");
      var form = ev.target;
      erro.hidden = true;
      fetch("/api/bugs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pagina: location.pathname,
          tipo: dados.get("tipo"),
          descricao: dados.get("descricao"),
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.erro) {
            erro.textContent = d.erro;
            erro.hidden = false;
            return;
          }
          form.hidden = true;
          sucesso.textContent = "✅ Bug registrado com sucesso. Obrigado!";
          sucesso.hidden = false;
          setTimeout(fechar, 1800);
        })
        .catch(function () {
          erro.textContent = "Não consegui falar com o Painel do Mestre.";
          erro.hidden = false;
        });
    });
  }

  function iniciar() {
    if (document.body.dataset.bugReportLigado) return;
    document.body.dataset.bugReportLigado = "1";
    document.body.addEventListener("click", function (ev) {
      if (ev.target.closest("[data-abrir-bug-report]")) abrirPopup();
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
