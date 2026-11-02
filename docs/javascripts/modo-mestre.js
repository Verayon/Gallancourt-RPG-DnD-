/* Botão de Modo Mestre no cabeçalho, ao lado do alternador claro/escuro do tema (ver
 * hooks/gallancourt.py — não vem mais embutido na página; este script injeta direto no
 * cabeçalho do Material, que já existe em toda página). Login/logout acontecem num popup
 * simples, sem navegar pra outra página — POST em /api/auth/entrar (mesma sessão/senha do
 * Painel), e a página atual recarrega sozinha ao confirmar.
 */
(function () {
  "use strict";

  function escapeHtml(valor) {
    return String(valor == null ? "" : valor)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function abrirPopup() {
    if (document.getElementById("modo-mestre-popup")) return;
    var popup = document.createElement("div");
    popup.id = "modo-mestre-popup";
    popup.className = "modo-mestre-popup";
    popup.innerHTML =
      '<div class="modo-mestre-popup__caixa">' +
      '<button type="button" class="botao-remover modo-mestre-popup__fechar" data-acao="fechar">× Fechar</button>' +
      "<h3>🔑 Entrar como Mestre</h3>" +
      '<form data-acao="entrar">' +
      '<input type="password" name="senha" placeholder="Senha" autofocus required>' +
      '<button type="submit" class="botao-principal">Confirmar</button>' +
      "</form>" +
      '<p class="ajuda modo-mestre-popup__erro" hidden></p>' +
      "</div>";
    document.body.appendChild(popup);

    function fechar() { popup.remove(); }

    popup.addEventListener("click", function (ev) {
      if (ev.target === popup || ev.target.closest('[data-acao="fechar"]')) fechar();
    });
    popup.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var senha = new FormData(ev.target).get("senha");
      var erro = popup.querySelector(".modo-mestre-popup__erro");
      fetch("/api/auth/entrar", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ senha: senha }),
      })
        .then(function (r) { return r.json(); })
        .then(function (d) {
          if (d.autenticado) {
            location.reload();
          } else {
            erro.textContent = d.erro || "Senha incorreta.";
            erro.hidden = false;
          }
        })
        .catch(function () {
          erro.textContent = "Não consegui falar com o Painel do Mestre.";
          erro.hidden = false;
        });
    });
  }

  function sair() {
    fetch("/api/auth/sair", { method: "POST" }).then(function () { location.reload(); });
  }

  function inserirBotao() {
    if (document.getElementById("modo-mestre-botao")) return;
    var opcaoPaleta = document.querySelector('[data-md-component="palette"]');
    if (!opcaoPaleta) return;
    var botao = document.createElement("button");
    botao.type = "button";
    botao.id = "modo-mestre-botao";
    botao.className = "md-header__button md-icon modo-mestre-botao";
    botao.textContent = "🔑";
    botao.title = "Entrar como Mestre";
    opcaoPaleta.insertAdjacentElement("afterend", botao);

    botao.addEventListener("click", function () {
      if (botao.dataset.autenticado === "1") sair();
      else abrirPopup();
    });

    atualizarEstado(botao);
  }

  function atualizarEstado(botao) {
    fetch("/api/auth/estado")
      .then(function (r) { return r.json(); })
      .then(function (d) {
        botao.dataset.autenticado = d.autenticado ? "1" : "0";
        botao.textContent = d.autenticado ? "🛡️" : "🔑";
        botao.title = d.autenticado ? "Modo Mestre ativo — clique para sair" : "Entrar como Mestre";
        botao.classList.toggle("modo-mestre-botao--ativo", !!d.autenticado);
      })
      .catch(function () { /* sem o Painel rodando, o botão só continua como está */ });
  }

  function iniciar() {
    inserirBotao();
  }

  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(iniciar);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
