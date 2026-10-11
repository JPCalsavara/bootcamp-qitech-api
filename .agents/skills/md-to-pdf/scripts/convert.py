#!/usr/bin/env python3
"""Script de conversão de RFCs em Markdown para PDFs de alta qualidade técnica via Pandoc, XeLaTeX e Mermaid-CLI.

Este script é o motor da skill 'md-to-pdf'.
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = SKILL_DIR / "template.tex"
LUA_FILTER = SKILL_DIR / "callouts.lua"
MERMAID_CONFIG = SKILL_DIR / "mermaid-config.json"
MERMAID_CSS = SKILL_DIR / "mermaid-theme.css"
PUPPETEER_CONFIG = SKILL_DIR / "puppeteer-config.json"
DEFAULT_OUTPUT_DIR = Path("docs/pdf").resolve()


def ensure_pandoc() -> str:
    """Verifica e garante que o Pandoc esteja instalado e disponível."""
    pandoc_path = shutil.which("pandoc")
    if pandoc_path:
        return pandoc_path

    user_local_pandoc = Path.home() / ".local" / "bin" / "pandoc"
    if user_local_pandoc.exists() and os.access(user_local_pandoc, os.X_OK):
        os.environ["PATH"] = f"{user_local_pandoc.parent}:{os.environ.get('PATH', '')}"
        return str(user_local_pandoc)

    print("⚠️ Pandoc não encontrado no sistema. Baixando binário oficial standalone para ~/.local/bin...")
    user_bin = Path.home() / ".local" / "bin"
    user_bin.mkdir(parents=True, exist_ok=True)

    url = "https://github.com/jgm/pandoc/releases/download/3.6.3/pandoc-3.6.3-linux-amd64.tar.gz"
    cmd = f"curl -fsSL {url} | tar -xz -C {user_bin} --strip-components=2 pandoc-3.6.3/bin/pandoc"
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0 or not user_local_pandoc.exists():
        sys.exit("❌ Erro ao baixar e instalar o Pandoc standalone.")

    os.chmod(user_local_pandoc, 0o755)
    os.environ["PATH"] = f"{user_bin}:{os.environ.get('PATH', '')}"
    print("✅ Pandoc instalado com sucesso em ~/.local/bin/pandoc!")
    return str(user_local_pandoc)


def ensure_xelatex() -> str:
    """Valida a presença do XeLaTeX."""
    xelatex_path = shutil.which("xelatex")
    if not xelatex_path:
        sys.exit("❌ XeLaTeX não encontrado. Instale o pacote texlive-xetex.")
    return xelatex_path


def ensure_npx() -> str:
    """Valida a presença do npx para o mermaid-cli."""
    npx_path = shutil.which("npx")
    if not npx_path:
        sys.exit("❌ npx (Node.js) não encontrado. Necessário para compilar diagramas Mermaid.")
    return npx_path


def parse_metadata(markdown_text: str) -> dict:
    """Extrai metadados do cabeçalho da RFC para preenchimento no template LaTeX."""
    metadata = {
        "title": "Request For Comments",
        "status": "Em Revisão",
        "date": "2026",
        "version": "1.0",
        "author": "CoreBank MEI Architecture Team",
    }

    # Título principal (# RFC — ...)
    title_match = re.search(r"^#\s+RFC\s*[—–-]\s*(.+)$", markdown_text, re.MULTILINE)
    if title_match:
        metadata["title"] = title_match.group(1).strip()
    else:
        first_h1 = re.search(r"^#\s+(.+)$", markdown_text, re.MULTILINE)
        if first_h1:
            metadata["title"] = first_h1.group(1).strip()

    # Tabela de metadados padrão da RFC (| **Status** | ... |)
    status_match = re.search(r"\|\s*\*\*Status\*\*\s*\|\s*([^|\n]+)\|", markdown_text, re.IGNORECASE)
    if status_match:
        metadata["status"] = status_match.group(1).strip()

    team_match = re.search(r"\|\s*\*\*Time\*\*\s*\|\s*([^|\n]+)\|", markdown_text, re.IGNORECASE)
    if team_match:
        metadata["author"] = team_match.group(1).strip()

    date_match = re.search(r"\|\s*\*\*Data\*\*\s*\|\s*([^|\n]+)\|", markdown_text, re.IGNORECASE)
    if date_match:
        metadata["date"] = date_match.group(1).strip()

    version_match = re.search(r"\|\s*\*\*Versão\*\*\s*\|\s*([^|\n]+)\|", markdown_text, re.IGNORECASE)
    if version_match:
        metadata["version"] = version_match.group(1).strip()

    return metadata


def enrich_mermaid_code(code: str) -> str:
    """Aplica cores e formatos semânticos exigidos pelo usuário nos fluxogramas:
    - Início: Círculo Verde
    - Fim/Erro: Círculo/Terminal Vermelho
    - Sucesso: Círculo Verde
    - Execução: Retângulo Azul
    - Condicionais/Loops: Losango Amarelo
    """
    lines = code.splitlines()
    injected_styles = []

    # Se for flowchart ou graph, aplicar classes semânticas
    if re.search(r"^\s*(flowchart|graph)\b", code, re.MULTILINE):
        injected_styles.append("    classDef startNode fill:#dcfce7,stroke:#16a34a,stroke-width:2.5px,color:#14532d;")
        injected_styles.append("    classDef endNode fill:#fee2e2,stroke:#dc2626,stroke-width:2.5px,color:#7f1d1d;")
        injected_styles.append("    classDef successNode fill:#dcfce7,stroke:#16a34a,stroke-width:2.5px,color:#14532d;")
        injected_styles.append("    classDef execNode fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1;")
        injected_styles.append("    classDef condNode fill:#fef9c3,stroke:#ca8a04,stroke-width:2px,color:#854d0e;")

        for line in lines:
            # Detecta Início: START((...)) ou nós com 'Início'
            start_nodes = re.findall(r"\b([A-Za-z0-9_]+)\s*\(\(.*?(?:Início|Inicio|Start).*?\)\)", line, re.IGNORECASE)
            for node in start_nodes:
                injected_styles.append(f"    class {node} startNode;")

            # Detecta Fim/Erro: ERR_... ou nós com 'Error', 'Fim', 'Terminal'
            end_nodes = re.findall(r"\b([A-Za-z0-9_]+)\s*(?:\[|\(|\{).*?(?:Error|Erro|Fim|Terminal|Rejected|REJECT).*?(?:\]|\)|\})", line, re.IGNORECASE)
            for node in end_nodes:
                injected_styles.append(f"    class {node} endNode;")

            # Detecta Sucesso terminal: SUCCESS((...)) ou nós com 'Success'/'Aprovado'
            success_nodes = re.findall(r"\b([A-Za-z0-9_]+)\s*\(\(.*?(?:Success|Sucesso|Aprovado|Provisionadas).*?\)\)", line, re.IGNORECASE)
            for node in success_nodes:
                injected_styles.append(f"    class {node} successNode;")

            # Detecta Execução: ID["..."] (retângulos de etapas)
            exec_nodes = re.findall(r"\b([A-Za-z0-9_]+)\s*\[\".*?\"\]", line)
            for node in exec_nodes:
                if not any(k in node.lower() for k in ["err", "error", "reject", "fail"]):
                    injected_styles.append(f"    class {node} execNode;")

            # Detecta Condicionais: ID{"..."} (losangos)
            cond_nodes = re.findall(r"\b([A-Za-z0-9_]+)\s*\{\".*?\"\}", line)
            for node in cond_nodes:
                injected_styles.append(f"    class {node} condNode;")

    return code + "\n" + "\n".join(injected_styles)


def render_mermaid_diagrams(text: str, temp_dir: Path) -> str:
    """Localiza todos os blocos de diagramas Mermaid, renderiza via mermaid-cli e substitui por figuras LaTeX."""
    mermaid_pattern = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)
    diagram_count = 0

    def replacer(match: re.Match) -> str:
        nonlocal diagram_count
        diagram_count += 1
        raw_code = match.group(1)
        enriched_code = enrich_mermaid_code(raw_code)

        mmd_file = temp_dir / f"diagram_{diagram_count}.mmd"
        png_file = temp_dir / f"diagram_{diagram_count}.png"

        mmd_file.write_text(enriched_code, encoding="utf-8")

        # Execução do mermaid-cli via npx
        cmd = [
            "npx",
            "-y",
            "@mermaid-js/mermaid-cli",
            "-i",
            str(mmd_file),
            "-o",
            str(png_file),
            "-c",
            str(MERMAID_CONFIG),
            "-C",
            str(MERMAID_CSS),
            "-p",
            str(PUPPETEER_CONFIG),
            "-s",
            "2",
            "-b",
            "transparent",
        ]

        print(f"   📊 Renderizando diagrama Mermaid #{diagram_count}...")
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0 or not png_file.exists():
            print(f"   ⚠️ Aviso: Falha ao renderizar diagrama #{diagram_count} com mermaid-cli: {res.stderr[:200]}")
            # Fallback para bloco de código legível caso o browser falhe
            return f"\n```text\n{raw_code}\n```\n"

        return f"\n\\begin{{figure}}[H]\n\\centering\n\\includegraphics[max width=0.92\\linewidth, max height=0.68\\textheight, keepaspectratio]{{{png_file.as_posix()}}}\n\\end{{figure}}\n"

    return mermaid_pattern.sub(replacer, text)


def process_github_callouts(text: str) -> str:
    """Converte alertas de Markdown do GitHub (> [!NOTE], etc.) para ambientes tcolorbox do LaTeX."""
    callout_map = {
        "NOTE": "calloutnote",
        "IMPORTANT": "calloutimportant",
        "WARNING": "calloutwarning",
        "CAUTION": "calloutwarning",
        "TIP": "callouttip",
    }

    # Regex para capturar blocos de callout:
    # > [!TIPO]
    # > linha 1
    # > linha 2
    pattern = re.compile(
        r"(?:^[ \t]*>[ \t]*\[!(NOTE|IMPORTANT|WARNING|CAUTION|TIP)\][ \t]*\n)((?:^[ \t]*>.*(?:\n|$))+)",
        re.MULTILINE,
    )

    def replacer(match: re.Match) -> str:
        callout_type = match.group(1).upper()
        content_lines = match.group(2).splitlines()
        env_name = callout_map.get(callout_type, "calloutnote")

        clean_lines = []
        for line in content_lines:
            cleaned = re.sub(r"^[ \t]*>[ \t]?", "", line)
            clean_lines.append(cleaned)

        body = "\n".join(clean_lines).strip()
        return f"\n::: {{{env_name}}}\n{body}\n:::\n\n"

    return pattern.sub(replacer, text)


def clean_markdown_links(text: str) -> str:
    """Normaliza links locais absolutos (ex: file:///home/.../0001.md) para textos legíveis."""
    # Transforma [ADR-0001](file:///.../0001-nome.md) em [ADR-0001](0001-nome.md) ou texto
    text = re.sub(r"\[([^\]]+)\]\(file:///[^)]+?/([^/)]+\.md)\)", r"[\1](\2)", text)
    # Remove tabela duplicada inicial de status/time se já capturada
    return text


def convert_file(input_md_path: Path, output_dir: Path) -> Path:
    """Executa o pipeline completo de conversão para um único arquivo Markdown."""
    print(f"\n🚀 Processando: {input_md_path.name}")
    content = input_md_path.read_text(encoding="utf-8")

    metadata = parse_metadata(content)
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_filename = input_md_path.stem + ".pdf"
    output_pdf_path = output_dir / pdf_filename

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)

        # 1. Renderizar diagramas Mermaid
        processed_text = render_mermaid_diagrams(content, temp_dir)

        # 2. Processar callouts e links
        processed_text = process_github_callouts(processed_text)
        processed_text = clean_markdown_links(processed_text)

        temp_md_file = temp_dir / "document_processed.md"
        temp_md_file.write_text(processed_text, encoding="utf-8")

        # 3. Invocar Pandoc com XeLaTeX
        cmd = [
            "pandoc",
            str(temp_md_file),
            "-o",
            str(output_pdf_path),
            "--pdf-engine=xelatex",
            f"--template={TEMPLATE_PATH}",
            f"--lua-filter={LUA_FILTER}",
            "--toc",
            "-N",
            "-V",
            "lang=pt-BR",
            f"-M",
            f"title={metadata['title']}",
            f"-M",
            f"status={metadata['status']}",
            f"-M",
            f"date={metadata['date']}",
            f"-M",
            f"version={metadata['version']}",
            f"-M",
            f"author={metadata['author']}",
            "--highlight-style=tango",
        ]

        print(f"   ⚙️ Compilando PDF via Pandoc e XeLaTeX...")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"❌ Erro na compilação do Pandoc/LaTeX:")
            print(res.stderr)
            raise RuntimeError(f"Falha ao compilar {input_md_path.name}")

    print(f"✨ Concluído com sucesso: {output_pdf_path}")
    return output_pdf_path


def main():
    parser = argparse.ArgumentParser(description="Converte RFCs em Markdown para PDF técnico estilizado.")
    parser.add_argument("input_files", nargs="*", help="Caminho para arquivos Markdown individuais.")
    parser.add_argument("--all", action="store_true", help="Converte todas as RFCs em docs/rfc/*.md.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Diretório de saída para os PDFs (padrão: {DEFAULT_OUTPUT_DIR}).",
    )

    args = parser.parse_args()

    ensure_pandoc()
    ensure_xelatex()
    ensure_npx()

    out_dir = Path(args.output_dir).resolve()

    target_files = []
    if args.all:
        rfc_files = sorted(glob.glob("docs/rfc/*.md"))
        target_files.extend([Path(f) for f in rfc_files])
    elif args.input_files:
        for f in args.input_files:
            p = Path(f)
            if p.is_file():
                target_files.append(p)
            else:
                print(f"⚠️ Arquivo não encontrado: {f}")
    else:
        # Se nenhum argumento for passado, exibe o help
        parser.print_help()
        sys.exit(1)

    if not target_files:
        print("Nenhum arquivo válido encontrado para conversão.")
        sys.exit(0)

    print(f"\n📦 Iniciando pipeline 'md-to-pdf' para {len(target_files)} documento(s)...")
    success_count = 0
    for target in target_files:
        try:
            convert_file(target, out_dir)
            success_count += 1
        except Exception as e:
            print(f"❌ Falha ao processar {target}: {e}")

    print(f"\n🎉 Processamento finalizado: {success_count}/{len(target_files)} PDFs gerados em {out_dir}\n")


if __name__ == "__main__":
    main()
