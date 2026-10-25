---
name: testar-site
description: Roda o teste fixo do site de Gallancourt (scripts/testar_site.py) e resume o resultado. Use só quando o autor pedir para testar ou validar o site.
disable-model-invocation: true
argument-hint: "[--sem-navegador] [--sem-painel]"
allowed-tools: Bash(python scripts/testar_site.py*), Bash(python3 scripts/testar_site.py*)
---

# Testar o site

O teste é **fixo**: valida sempre as mesmas 21 coisas (cálculos da ficha 5e e da linha do tempo,
menu, relações, build, páginas geradas, navegador e Painel) numa **cópia temporária** — nunca
altera o projeto.

## Passos

1. Rode, a partir da raiz do projeto (use `python3` se `python` não existir):

   ```bash
   python scripts/testar_site.py $ARGUMENTS
   ```

   Sem o Playwright instalado, os testes de navegador aparecem como PULADO — isso não é falha.
   Leva cerca de 30 segundos.

2. **Leia só o fim da saída**: a linha de resumo (`N passaram · N falharam · N pulados`) e as
   linhas com ❌. Não leia o código do teste nem do site se tudo passou.

3. Responda ao autor em poucas linhas:
   - tudo passou → diga isso e o número de verificações;
   - algo falhou → para cada ❌: o que deveria acontecer, o que aconteceu (o detalhe da linha) e a
     causa provável. Só então, se precisar, abra o arquivo envolvido para confirmar.
   - houve PULADO → diga o que faltou instalar (o detalhe da linha explica).

4. **Não corrija nada sem o autor pedir.** Proponha a correção e espere.

5. **Nunca altere o teste para fazê-lo passar.** Se uma falha vier de uma mudança combinada com o
   autor (ex.: um item novo no menu), atualize as constantes no topo de `scripts/testar_site.py`
   (`MENU_TOPO`, `MENU_WIKI`, `COLUNAS_NPC`) só depois que ele confirmar.
