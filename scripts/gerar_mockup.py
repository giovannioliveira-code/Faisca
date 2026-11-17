#!/usr/bin/env python3
"""
Gerador de mockups de UI do Faísca.

Em vez de pedir pra uma IA "desenhar" uma tela (o que sai com texto ilegível
e layout quebrado), este script monta HTML/CSS real a partir de uma lista de
campos, usando um design system simples e consistente. O resultado é:
  - um arquivo .html (reaproveitável, pode ser aberto e ajustado)
  - um arquivo .png (screenshot tirado com Playwright, pra visualizar rápido)

Uso:
    python3 gerar_mockup.py \
        --titulo "Cadastro de fornecedor" \
        --tipo formulario \
        --campos "Nome:text,E-mail:email,Telefone:tel,Observações:textarea" \
        --botao-principal "Salvar" \
        --botao-secundario "Cancelar" \
        --saida mockups/cadastro-fornecedor

Tipos suportados: formulario, lista, dashboard, detalhe
"""
import argparse
import html
import re
import unicodedata
from datetime import datetime
from pathlib import Path

CSS = """
:root {
  --bg: #f4f5f7;
  --surface: #ffffff;
  --border: #e2e4e9;
  --text: #1c1d21;
  --text-muted: #6b7076;
  --primary: #5b5bf0;
  --primary-text: #ffffff;
  --radius: 10px;
  --shadow: 0 1px 2px rgba(16, 17, 20, 0.04), 0 4px 10px rgba(16, 17, 20, 0.04);
  --font: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  display: flex;
  justify-content: center;
  padding: 40px 20px;
}
.tela {
  width: 100%;
  max-width: 560px;
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
  overflow: hidden;
}
.tela.larga { max-width: 860px; }
.cabecalho {
  padding: 24px 28px 20px;
  border-bottom: 1px solid var(--border);
}
.cabecalho h1 {
  margin: 0;
  font-size: 19px;
  font-weight: 600;
  letter-spacing: -0.01em;
}
.cabecalho p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-muted);
}
.corpo { padding: 24px 28px 28px; }
.campo { margin-bottom: 18px; }
.campo label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 6px;
  color: var(--text);
}
.campo input, .campo textarea, .campo select {
  width: 100%;
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #fbfbfc;
  color: var(--text-muted);
}
.campo textarea { resize: none; height: 72px; }
.rodape {
  padding: 18px 28px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
.btn {
  padding: 9px 18px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 8px;
  border: 1px solid transparent;
  cursor: default;
  font-family: inherit;
}
.btn-principal { background: var(--primary); color: var(--primary-text); }
.btn-secundario { background: var(--surface); color: var(--text); border-color: var(--border); }

table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
th {
  text-align: left;
  padding: 10px 12px;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  font-weight: 600;
}
td {
  padding: 11px 12px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}
tr:last-child td { border-bottom: none; }
.pill {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 500;
  background: #eef0ff;
  color: var(--primary);
}

.grade-kpi {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 14px;
}
.kpi {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px 18px;
  background: #fbfbfc;
}
.kpi .valor { font-size: 24px; font-weight: 600; letter-spacing: -0.01em; }
.kpi .label { font-size: 12.5px; color: var(--text-muted); margin-top: 2px; }

.detalhe-linha {
  display: flex;
  justify-content: space-between;
  padding: 13px 0;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.detalhe-linha:last-child { border-bottom: none; }
.detalhe-linha .rotulo { color: var(--text-muted); }
.detalhe-linha .valor { font-weight: 500; text-align: right; }
"""

TIPOS_INPUT = {"email", "tel", "number", "date", "password"}


def slugify(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    texto = re.sub(r"[^a-zA-Z0-9]+", "-", texto).strip("-").lower()
    return texto or "tela"


def sentence_case(texto: str) -> str:
    """Converte para sentence case: só a primeira letra maiúscula."""
    texto = texto.strip()
    if not texto:
        return texto
    return texto[0].upper() + texto[1:].lower()


def parse_campos(bruto: str) -> list[tuple[str, str]]:
    """'Nome:text,Email:email' -> [('Nome', 'text'), ('Email', 'email')]"""
    campos = []
    for parte in bruto.split(","):
        parte = parte.strip()
        if not parte:
            continue
        if ":" in parte:
            label, valor = parte.split(":", 1)
        else:
            label, valor = parte, "text"
        campos.append((label.strip(), valor.strip() or "text"))
    return campos


def montar_formulario(campos: list[tuple[str, str]]) -> str:
    blocos = []
    for label, tipo in campos:
        esc = html.escape(label)
        tipo_norm = tipo.lower()
        if tipo_norm == "textarea":
            campo_html = f'<textarea placeholder="{esc}..."></textarea>'
        elif tipo_norm == "select":
            campo_html = f'<select><option>{esc}</option></select>'
        else:
            tipo_input = tipo_norm if tipo_norm in TIPOS_INPUT else "text"
            campo_html = f'<input type="{tipo_input}" placeholder="{esc}..." readonly>'
        blocos.append(f'<div class="campo"><label>{esc}</label>{campo_html}</div>')
    return "\n".join(blocos)


def montar_lista(campos: list[tuple[str, str]], linhas: int = 4) -> str:
    ths = "".join(f"<th>{html.escape(label)}</th>" for label, _ in campos)
    trs = []
    for i in range(1, linhas + 1):
        tds = []
        for j, (label, tipo) in enumerate(campos):
            if j == 0:
                tds.append(f"<td>{html.escape(label)} {i:02d}</td>")
            elif tipo.lower() == "status":
                tds.append('<td><span class="pill">Ativo</span></td>')
            else:
                tds.append(f"<td>—</td>")
        trs.append(f"<tr>{''.join(tds)}</tr>")
    return f"<table><thead><tr>{ths}</tr></thead><tbody>{''.join(trs)}</tbody></table>"


def montar_dashboard(campos: list[tuple[str, str]]) -> str:
    """Campos no formato 'Rótulo:valor' viram cartões de KPI."""
    cards = []
    for label, valor in campos:
        v = valor if valor and valor != "text" else "—"
        cards.append(
            f'<div class="kpi"><div class="valor">{html.escape(v)}</div>'
            f'<div class="label">{html.escape(label)}</div></div>'
        )
    return f'<div class="grade-kpi">{"".join(cards)}</div>'


def montar_detalhe(campos: list[tuple[str, str]]) -> str:
    linhas = []
    for label, valor in campos:
        v = valor if valor and valor != "text" else "—"
        linhas.append(
            f'<div class="detalhe-linha"><span class="rotulo">{html.escape(label)}</span>'
            f'<span class="valor">{html.escape(v)}</span></div>'
        )
    return "".join(linhas)


def gerar_html(titulo: str, descricao: str, tipo: str, campos: list[tuple[str, str]],
               botao_principal: str, botao_secundario: str) -> str:
    larga = " larga" if tipo in ("lista", "dashboard") else ""
    if tipo == "formulario":
        corpo = montar_formulario(campos)
    elif tipo == "lista":
        corpo = montar_lista(campos)
    elif tipo == "dashboard":
        corpo = montar_dashboard(campos)
    elif tipo == "detalhe":
        corpo = montar_detalhe(campos)
    else:
        raise ValueError(f"tipo desconhecido: {tipo}")

    rodape = ""
    if botao_principal or botao_secundario:
        btns = ""
        if botao_secundario:
            btns += f'<button class="btn btn-secundario">{html.escape(sentence_case(botao_secundario))}</button>'
        if botao_principal:
            btns += f'<button class="btn btn-principal">{html.escape(sentence_case(botao_principal))}</button>'
        rodape = f'<div class="rodape">{btns}</div>'

    desc_html = f"<p>{html.escape(descricao)}</p>" if descricao else ""

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)}</title>
<style>{CSS}</style>
</head>
<body>
  <div class="tela{larga}">
    <div class="cabecalho">
      <h1>{html.escape(titulo)}</h1>
      {desc_html}
    </div>
    <div class="corpo">{corpo}</div>
    {rodape}
  </div>
</body>
</html>"""


def tirar_screenshot(caminho_html: Path, caminho_png: Path, largo: bool) -> None:
    from playwright.sync_api import sync_playwright

    largura = 960 if largo else 640
    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": largura, "height": 100})
        pagina.goto(f"file://{caminho_html.resolve()}")
        pagina.wait_for_timeout(150)
        # Screenshot só do cartão (.tela), não da página toda: evita margem em branco
        # quando o conteúdo é menor que a altura padrão da viewport.
        pagina.locator(".tela").screenshot(path=str(caminho_png))
        navegador.close()


def main():
    ap = argparse.ArgumentParser(description="Gera mockup de UI (HTML + PNG) a partir de campos.")
    ap.add_argument("--titulo", required=True)
    ap.add_argument("--tipo", required=True, choices=["formulario", "lista", "dashboard", "detalhe"])
    ap.add_argument("--campos", required=True, help="Ex.: 'Nome:text,Email:email' ou 'Total de vendas:R$ 12.400'")
    ap.add_argument("--descricao", default="")
    ap.add_argument("--botao-principal", dest="botao_principal", default="")
    ap.add_argument("--botao-secundario", dest="botao_secundario", default="")
    ap.add_argument("--saida", default=None, help="Caminho base (sem extensão) para os arquivos gerados")
    ap.add_argument("--sem-screenshot", action="store_true", help="Só gera o HTML, pula o PNG")
    args = ap.parse_args()

    campos = parse_campos(args.campos)
    conteudo = gerar_html(
        titulo=args.titulo,
        descricao=args.descricao,
        tipo=args.tipo,
        campos=campos,
        botao_principal=args.botao_principal,
        botao_secundario=args.botao_secundario,
    )

    if args.saida:
        base = Path(args.saida)
    else:
        carimbo = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = Path("mockups") / f"{slugify(args.titulo)}-{carimbo}"
    base.parent.mkdir(parents=True, exist_ok=True)

    caminho_html = base.with_suffix(".html")
    caminho_html.write_text(conteudo, encoding="utf-8")
    print(f"HTML gerado: {caminho_html}")

    if not args.sem_screenshot:
        caminho_png = base.with_suffix(".png")
        tirar_screenshot(caminho_html, caminho_png, largo=args.tipo in ("lista", "dashboard"))
        print(f"PNG gerado: {caminho_png}")


if __name__ == "__main__":
    main()
