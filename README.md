# Faísca — gerador de mockups de UI

Agente de design para migração de sistemas (desafio Agent Building, MJV).

Como o Agent Studio só integra com GitHub (sem Figma), o Faísca gera telas como
**HTML/CSS real**, não como imagem de IA. Isso evita o problema clássico de
geradores de imagem (texto ilegível, layout quebrado) — o texto sai nítido
porque é texto de verdade, renderizado por um navegador.

## Como funciona

1. O Faísca (ou você, manualmente) dispara o workflow **Gerar mockup de UI**
   (`.github/workflows/gerar-mockup.yml`) pela API do GitHub ou pela aba
   **Actions** deste repositório.
2. O workflow roda `scripts/gerar_mockup.py`, que monta a tela a partir dos
   campos informados, usando um design system simples e consistente.
3. Tira um screenshot com Playwright e commita dois arquivos em `mockups/`:
   - `<slug>-<data>.html` — a tela em si, reaproveitável
   - `<slug>-<data>.png` — a imagem, pra visualizar rápido

## Rodando manualmente (teste local)

```bash
pip install -r scripts/requirements.txt
playwright install chromium

python3 scripts/gerar_mockup.py \
  --titulo "Cadastro de fornecedor" \
  --tipo formulario \
  --campos "Nome:text,E-mail:email,Telefone:tel,Observações:textarea" \
  --botao-principal "Salvar" \
  --botao-secundario "Cancelar"
```

## Tipos de tela suportados

| Tipo         | Formato de `--campos`                         | Uso                                  |
|--------------|------------------------------------------------|---------------------------------------|
| `formulario` | `Rótulo:tipo` (text, email, tel, textarea, select) | Telas de cadastro/edição |
| `lista`      | `Rótulo:tipo` (use `status` para uma coluna com pill) | Tabelas/listagens        |
| `dashboard`  | `Rótulo:valor`                                  | Cartões de KPI                        |
| `detalhe`    | `Rótulo:valor`                                  | Visualização somente leitura          |

Botões (`--botao-principal`, `--botao-secundario`) sempre saem em **sentence
case** (só a primeira letra maiúscula), seguindo o padrão de copy de UI usado
nos outros projetos.

## Conectando no Agent Studio

1. Em **Configurações → Integrações → GitHub**, conecte sua conta.
2. Em **Permissões**, habilite a operação de **disparar workflow** (grupo
   "Criar e enviar" ou "Organizar e alterar" — a lista de 877 operações é a
   API do GitHub via Composio).
3. Instrua o Faísca a disparar `gerar-mockup.yml` neste repositório, passando
   `titulo`, `tipo`, `campos` e, se quiser, `descricao`/`botao_principal`/
   `botao_secundario`.
4. O resultado aparece commitado em `mockups/` — e um resumo com a imagem
   aparece na própria execução do workflow (aba Actions → Summary).
