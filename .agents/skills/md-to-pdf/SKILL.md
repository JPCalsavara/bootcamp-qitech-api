---
name: md-to-pdf
description: Converte RFCs e documentos Markdown em PDFs de alta qualidade técnica via Pandoc, XeLaTeX e diagramas Mermaid estilizados com paleta semântica.
---

# Skill: `md-to-pdf`

Esta habilidade automatiza o pipeline de compilação de documentos técnicos (RFCs, ADRs e especificações de arquitetura) em formato Markdown para relatórios e manuais em PDF com tipografia e diagramação de nível editorial.

## Quando Utilizar
- Quando o usuário pedir para gerar, exportar ou transformar RFCs em PDF.
- Quando for necessário imprimir ou compartilhar especificações técnicas com stakeholders ou em apresentações de arquitetura.
- Quando novos diagramas Mermaid precisarem ser compilados com cores semânticas padronizadas.

## O Que a Pipeline Faz

1. **Gestão Transparente de Dependências:**
   - Detecta e utiliza o `pandoc`, baixando automaticamente o binário standalone oficial para `~/.local/bin/` se ausente (sem precisar de privilégios de `sudo`).
   - Utiliza o motor **XeLaTeX** com fontes modernas (DejaVu Sans) e pacotes `tcolorbox`, `fancyhdr`, `booktabs` e `hyperref`.

2. **Diagramas Mermaid Semânticos:**
   - Extrai automaticamente os blocos ````mermaid` dos arquivos Markdown.
   - Aplica a padronização visual exigida:
     - **Início:** Círculo Verde (`#dcfce7`, borda `#16a34a`)
     - **Fim / Erros:** Círculo / Terminal Vermelho (`#fee2e2`, borda `#dc2626`)
     - **Sucesso:** Círculo Verde (`#dcfce7`, borda `#16a34a`)
     - **Execução:** Retângulo Azul (`#e0f2fe`, borda `#0284c7`)
     - **Condicionais e Loops:** Losango Amarelo (`#fef9c3`, borda `#ca8a04`)
   - Compila em PNGs de altíssima densidade (1800px) com fundo transparente via `npx @mermaid-js/mermaid-cli` e o Google Chrome local com modo headless seguro (`--no-sandbox`).

3. **Callouts GitHub para LaTeX (`tcolorbox`):**
   - Converte `> [!NOTE]`, `> [!IMPORTANT]`, `> [!WARNING]` e `> [!TIP]` em caixas coloridas destacadas com bordas arredondadas e títulos temáticos.

4. **Metadados e Layout:**
   - Extrai Título, Status da RFC, Versão, Data e Time diretamente do Markdown e injeta no cabeçalho institucional do PDF.
   - Gera sumário navegável (TOC) com links internos.

---

## Como Executar

### 1. Converter uma RFC específica
```bash
python .agents/skills/md-to-pdf/scripts/convert.py docs/rfc/rfc-01-onboarding-identidade-contas.md
```

### 2. Converter todas as RFCs do projeto em lote
```bash
python .agents/skills/md-to-pdf/scripts/convert.py --all
```

### 3. Especificar diretório de saída customizado
```bash
python .agents/skills/md-to-pdf/scripts/convert.py --all --output-dir docs/pdf/
```

Os arquivos finais serão salvos em `docs/pdf/<nome-do-arquivo>.pdf`.

---

## Customização Visual

- **Template LaTeX:** Modifique `.agents/skills/md-to-pdf/template.tex` para alterar margens, fontes, logos ou cabeçalhos.
- **Configurações Gerais de Diagramas:** Modifique `.agents/skills/md-to-pdf/mermaid-config.json`.
- **Paleta de Cores dos Diagramas:** Modifique `.agents/skills/md-to-pdf/mermaid-theme.css`.
