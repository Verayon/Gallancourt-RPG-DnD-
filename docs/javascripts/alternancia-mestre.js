/* Alternador Normal/Mestre no topo de cada página de sessão (ver admin/wiki_data.py::
 * _modelo_sessao e hooks/gallancourt.py::_ABERTURA_ALTERNANCIA_MESTRE). Clicar num botão só
 * troca o atributo `data-modo` da raiz `.alternancia-mestre` — o CSS (extra.css) decide o que
 * fica visível; o painel de iniciativa em si (painel-iniciativa.js) continua montado o tempo
 * todo, só escondido quando o modo é "normal".
 */
(function () {
  "use strict";

  function ligar(raiz) {
    var botoes = raiz.querySelectorAll(".alternancia-mestre__botao");
    botoes.forEach(function (botao) {
      botao.addEventListener("click", function () {
        var alvo = botao.getAttribute("data-alvo");
        raiz.setAttribute("data-modo", alvo);
        botoes.forEach(function (b) {
          b.classList.toggle("alternancia-mestre__botao--ativo", b === botao);
        });
      });
    });
  }

  function iniciar() {
    document.querySelectorAll(".alternancia-mestre[data-modo]").forEach(ligar);
  }

  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(iniciar);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
