#!/usr/bin/env python3
"""
Gerador de mockups de UI do Faísca — visual inspirado nos design tokens
abertos do Cloudscape (AWS, licença Apache 2.0): azul primário, Open Sans,
cantos de 8px, espaçamento em múltiplos de 4px. Agora renderiza um console
completo (cabeçalho + menu lateral + conteúdo), não só um cartão solto.

Em vez de pedir pra uma IA "desenhar" uma tela (o que sai com texto ilegível
e layout quebrado), este script monta HTML/CSS real a partir de uma lista de
campos. O resultado é:
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
  /* Tokens no espírito do Cloudscape (AWS, Apache 2.0): azul primário,
     Open Sans, raio de 8px, espaçamento em múltiplos de 4px. */
  --bg: #f2f3f3;
  --surface: #ffffff;
  --border: #e9ebed;
  --border-strong: #d1d5db;
  --text: #16191f;
  --text-muted: #5f6b7a;
  --primary: #0972d3;
  --primary-hover: #075fb0;
  --primary-text: #ffffff;
  --radius: 8px;
  --radius-sm: 6px;
  --shadow: 0 1px 2px rgba(15, 20, 28, 0.06), 0 2px 8px rgba(15, 20, 28, 0.05);
  --font: "Open Sans", -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --topbar-bg: #0f1b2a;
  --topbar-text: #d4dde8;
  --sidebar-bg: #ffffff;
  --sidebar-active-bg: #f0f7ff;
  --success-bg: #e9f7ea; --success-text: #16794b;
  --neutral-bg: #eef0f2; --neutral-text: #5f6b7a;
}
* { box-sizing: border-box; }
html, body { margin: 0; height: 100%; }
body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  -webkit-font-smoothing: antialiased;
}

/* ---------- console shell ---------- */
.console { display: flex; flex-direction: column; height: 800px; width: 1280px; overflow: hidden; }

.topbar {
  height: 52px;
  flex: 0 0 auto;
  background: var(--topbar-bg);
  color: var(--topbar-text);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}
.topbar .brand { display: flex; align-items: center; gap: 8px; font-weight: 600; font-size: 14px; color: #fff; }
.topbar .brand .dot { width: 8px; height: 8px; border-radius: 2px; background: var(--primary); display: inline-block; }
.topbar .topbar-right { display: flex; align-items: center; gap: 16px; font-size: 12.5px; color: var(--topbar-text); }
.topbar .avatar {
  width: 26px; height: 26px; border-radius: 50%; background: #233447;
  display: flex; align-items: center; justify-content: center; font-size: 11px; color: #cfd8e3;
}

.shell { flex: 1 1 auto; display: flex; min-height: 0; }

.sidebar {
  width: 220px;
  flex: 0 0 auto;
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  padding: 16px 0;
  overflow-y: auto;
}
.sidebar ul { list-style: none; margin: 0; padding: 0; }
.sidebar li {
  padding: 9px 20px;
  font-size: 13.5px;
  color: var(--text-muted);
  border-left: 3px solid transparent;
  cursor: default;
}
.sidebar li.active {
  color: var(--primary);
  font-weight: 600;
  background: var(--sidebar-active-bg);
  border-left-color: var(--primary);
}

.content { flex: 1 1 auto; overflow-y: auto; padding: 28px 32px; }

/* ---------- card (a "tela" em si, dentro do console) ---------- */
.tela {
  width: 100%;
  max-width: 760px;
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
  overflow: hidden;
}
.tela.larga { max-width: 100%; }

.cabecalho {
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border);
}
.cabecalho .trilha {
  font-size: 11.5px;
  color: var(--text-muted);
  margin: 0 0 6px;
  letter-spacing: 0.01em;
}
.cabecalho h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: var(--text);
}
.cabecalho p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-muted);
}
.corpo { padding: 24px; }
.campo { margin-bottom: 16px; }
.campo label {
  display: block;
  font-size: 12.5px;
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--text);
}
.campo input, .campo textarea, .campo select {
  width: 100%;
  padding: 9px 12px;
  font-size: 14px;
  font-family: inherit;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: #fbfbfc;
  color: var(--text-muted);
}
.campo input:focus, .campo textarea:focus, .campo select:focus { outline: none; border-color: var(--primary); }
.campo textarea { resize: none; height: 72px; }

.rodape {
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.btn {
  padding: 8px 16px;
  font-size: 13.5px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
  cursor: default;
  font-family: inherit;
}
.btn-principal { background: var(--primary); color: var(--primary-text); }
.btn-secundario { background: var(--surface); color: var(--text); border-color: var(--border-strong); }

/* ---------- tabela / lista ---------- */
.filtros { display: flex; gap: 8px; padding: 16px 24px 0; flex-wrap: wrap; }
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 10px; border-radius: 999px;
  background: var(--sidebar-active-bg); color: var(--primary);
  font-size: 12px; font-weight: 600; border: 1px solid #cfe3fa;
}
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
th {
  text-align: left;
  padding: 10px 16px;
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  background: #fafbfb;
  border-bottom: 1px solid var(--border);
  font-weight: 700;
}
td {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}
tr:last-child td { border-bottom: none; }
.pill {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 600;
}
.pill.ativo { background: var(--success-bg); color: var(--success-text); }
.pill.neutro { background: var(--neutral-bg); color: var(--neutral-text); }

/* ---------- empty state ---------- */
.empty-state {
  padding: 56px 24px;
  text-align: center;
}
.empty-state .icone {
  width: 40px; height: 40px; margin: 0 auto 12px;
  border-radius: 50%; background: var(--neutral-bg);
  display: flex; align-items: center; justify-content: center;
  color: var(--text-muted); font-size: 18px; font-weight: 700;
}
.empty-state h2 { margin: 0 0 4px; font-size: 15px; font-weight: 700; color: var(--text); }
.empty-state p { margin: 0; font-size: 13px; color: var(--text-muted); }

/* ---------- dashboard (kpis) ---------- */
.grade-kpi {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 16px;
}
.kpi {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  background: var(--surface);
  border-top: 3px solid var(--primary);
}
.kpi .valor { font-size: 26px; font-weight: 700; letter-spacing: -0.01em; color: var(--text); }
.kpi .label { font-size: 12.5px; color: var(--text-muted); margin-top: 4px; }

/* ---------- detalhe ---------- */
.detalhe-linha {
  display: flex;
  justify-content: space-between;
  padding: 13px 24px;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}
.detalhe-linha:last-child { border-bottom: none; }
.detalhe-linha .rotulo { color: var(--text-muted); }
.detalhe-linha .valor { font-weight: 600; text-align: right; color: var(--text); }
"""

TIPOS_INPUT = {"email", "tel", "number", "date", "password"}

NAV_ITEMS = ["Visão geral", "Pedidos", "Relatórios", "Configurações"]
NAV_ATIVO_POR_TIPO = {
    "formulario": "Pedidos",
    "lista": "Pedidos",
    "dashboard": "Visão geral",
    "detalhe": "Pedidos",
}


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


def montar_navegacao(tipo: str) -> str:
    ativo = NAV_ATIVO_POR_TIPO.get(tipo, NAV_ITEMS[0])
    itens = []
    for item in NAV_ITEMS:
        classe = ' class="active"' if item == ativo else ""
        itens.append(f"<li{classe}>{html.escape(item)}</li>")
    return "\n".join(itens)


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


def eh_vazio(campos: list[tuple[str, str]]) -> bool:
    """Detecta pedido de empty state: tipo 'empty' em algum campo, ou único campo é a mensagem."""
    return any(tipo.lower() in ("empty", "empty-state", "vazio") for _, tipo in campos)


def montar_lista(campos: list[tuple[str, str]], linhas: int = 4) -> str:
    if eh_vazio(campos):
        # campos[0] = (mensagem_principal, "empty"), campos[1:] = chips de filtro (rotulo:valor)
        mensagem = campos[0][0] if campos else "Nenhum registro encontrado."
        chips = campos[1:]
        chips_html = ""
        if chips:
            itens = "".join(
                f'<span class="chip">{html.escape(l)}: {html.escape(v)}</span>' for l, v in chips
            )
            chips_html = f'<div class="filtros">{itens}</div>'
        return (
            f'{chips_html}'
            f'<div class="empty-state">'
            f'<div class="icone">!</div>'
            f'<h2>{html.escape(mensagem)}</h2>'
            f'<p>A sua busca não retornou registros.</p>'
            f'</div>'
        )
    ths = "".join(f"<th>{html.escape(label)}</th>" for label, _ in campos)
    trs = []
    for i in range(1, linhas + 1):
        tds = []
        for j, (label, tipo) in enumerate(campos):
            if j == 0:
                tds.append(f"<td>{html.escape(label)} {i:02d}</td>")
            elif tipo.lower() == "status":
                tds.append('<td><span class="pill ativo">Ativo</span></td>')
            else:
                tds.append("<td>—</td>")
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
    vazio = tipo == "lista" and eh_vazio(campos)
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
    if not vazio and (botao_principal or botao_secundario):
        btns = ""
        if botao_secundario:
            btns += f'<button class="btn btn-secundario">{html.escape(sentence_case(botao_secundario))}</button>'
        if botao_principal:
            btns += f'<button class="btn btn-principal">{html.escape(sentence_case(botao_principal))}</button>'
        rodape = f'<div class="rodape">{btns}</div>'

    desc_html = f"<p>{html.escape(descricao)}</p>" if descricao else ""
    nav_html = montar_navegacao(tipo)

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo)}</title>
<style>{CSS}</style>
</head>
<body>
  <div class="console">
    <header class="topbar">
      <div class="brand"><span class="dot"></span> Console</div>
      <div class="topbar-right">
        <span>PT-BR</span>
        <div class="avatar">U</div>
      </div>
    </header>
    <div class="shell">
      <nav class="sidebar"><ul>{nav_html}</ul></nav>
      <main class="content">
        <div class="tela{larga}">
          <div class="cabecalho">
            <h1>{html.escape(titulo)}</h1>
            {desc_html}
          </div>
          <div class="corpo">{corpo}</div>
          {rodape}
        </div>
      </main>
    </div>
  </div>
</body>
</html>"""


def tirar_screenshot(caminho_html: Path, caminho_png: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        navegador = p.chromium.launch()
        pagina = navegador.new_page(viewport={"width": 1280, "height": 800})
        pagina.goto(f"file://{caminho_html.resolve()}")
        pagina.wait_for_timeout(150)
        pagina.screenshot(path=str(caminho_png))
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
        tirar_screenshot(caminho_html, caminho_png)
        print(f"PNG gerado: {caminho_png}")


if __name__ == "__main__":
    main()
