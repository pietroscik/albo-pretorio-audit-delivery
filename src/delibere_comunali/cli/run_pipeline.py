#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestrates the analysis/training/validation pipeline."""

import sys
import subprocess
from pathlib import Path
import argparse

def get_project_root() -> Path:
    """Trova la root del progetto cercando pyproject.toml."""
    path = Path(__file__).resolve()
    for _ in range(5):  # Max 5 livelli su
        if (path / "pyproject.toml").exists():
            return path
        path = path.parent
    return Path(__file__).resolve().parent.parent.parent.parent  # Fallback

PROJECT_ROOT = get_project_root()

def run_step(command, title, cwd=None, optional=False):
    print("\n" + "=" * 72)
    print(f"STEP: {title}")
    print(f"CMD : {' '.join(map(str, command))}")
    print("=" * 72)
    result = subprocess.run(command, cwd=cwd or PROJECT_ROOT)
    if result.returncode != 0:
        if optional:
            print(f"⚠️  Step opzionale fallito (skip): {title}")
            return result
        raise SystemExit(result.returncode)
    return result

def resolve_base_path(base: str, ente: str) -> str:
    base_path = Path(base)
    if (base_path / "albo_metadati.csv").exists() or (base_path / "albo_metadati.jsonl").exists():
        return str(base_path)
    parent = base_path.parent
    if (parent / "albo_metadati.csv").exists() or (parent / "albo_metadati.jsonl").exists():
        return str(parent)
    fallback = Path("data") / ente / "albo_download"
    return str(fallback)

def _module_command(module: str, extra_args=None):
    cmd = [sys.executable, "-m", module]
    if extra_args:
        cmd.extend(extra_args)
    return cmd

def _script_command(script_rel: str, extra_args=None):
    script = PROJECT_ROOT / script_rel
    cmd = [sys.executable, str(script)]
    if extra_args:
        cmd.extend(extra_args)
    return cmd

def _script_exists(script_rel: str) -> bool:
    return (PROJECT_ROOT / script_rel).exists()

def main() -> None:
    p = argparse.ArgumentParser(description="Pipeline orchestration")
    p.add_argument("--ente", required=True, help="ente identifier")
    p.add_argument("--base", default=None, help="base dir (optional)")
    p.add_argument("--adapter", help="adapter name (e.g. halley)")
    p.add_argument("--adapter-out", help="path for adapter jsonl output")
    p.add_argument("--limit", type=int, default=None)
    # LLM
    p.add_argument("--use-llm", action="store_true",
                    help="abilita arricchimento LLM nel parsing e audit")
    p.add_argument("--llm-provider", default=None,
                    help="provider LLM (openai, anthropic, ollama...)")
    p.add_argument("--llm-model", default=None,
                    help="modello LLM da usare")
    # Skip/only
    p.add_argument("--skip-scrape", action="store_true",
                    help="salta lo scraping")
    p.add_argument("--skip-clean", action="store_true",
                    help="salta la pulizia testi")
    p.add_argument("--skip-kg", action="store_true",
                    help="salta il Knowledge Graph")
    p.add_argument("--skip-audit", action="store_true",
                    help="salta il motore di audit")
    p.add_argument("--skip-validate", action="store_true",
                    help="salta la validazione output")
    p.add_argument("--skip-post-process", action="store_true",
                    help="salta il post-processing della classificazione")
    p.add_argument("--skip-orchestration", action="store_true",
                    help="salta la fase di coordinamento tra moduli")
    p.add_argument("--only-audit", action="store_true",
                    help="esegui solo audit")
    p.add_argument("--only-analyze", action="store_true",
                    help="esegui solo parsing/analyze")
    p.add_argument("--force", action="store_true",
               help="Ignora cache e forza ri-elaborazione")
    # Aggiungi il parametro per saltare l'analisi procedurale
    p.add_argument("--skip-procedural", action="store_true",
                   help="salta l'analisi procedurale")
    # Aggiungi il parametro per saltare il filtraggio dei file scaricati
    p.add_argument("--skip-filter-files", action="store_true",
                   help="salta il filtraggio dei file scaricati dallo scraper")
    args = p.parse_args()

    ente = args.ente
    base_arg = args.base or f"./data/{ente}/albo_download"
    resolved_base = resolve_base_path(base_arg, ente)
    limit_args = ["--limit", str(args.limit)] if args.limit else []

    # flag LLM da propagare agli step che li supportano
    llm_args = []
    if args.use_llm:
        if args.llm_provider:
            llm_args.extend(["--llm-provider", args.llm_provider])
        if args.llm_model:
            llm_args.extend(["--llm-model", args.llm_model])

    # Pipeline steps
    steps = []

    # Scraping (if not skipped)
    if not args.skip_scrape:
        scrape_args = ["--ente", ente, "--base", resolved_base] + limit_args
        if args.adapter:
            scrape_args.extend(["--adapter", args.adapter])
        if args.adapter_out:
            scrape_args.extend(["--adapter-out", args.adapter_out])
        steps.append((_module_command("delibere_comunali.scraping.new_albo_scraper", scrape_args), "Scraping"))

    # Filter downloaded files (if not skipped and scraping is not skipped)
    if not args.skip_scrape and not args.skip_filter_files:
        filter_args = ["--ente", ente, "--base", resolved_base]
        steps.append((_script_command("scripts/filter_downloaded_files.py", filter_args), "Filter Downloaded Files"))

    # Analyze/Parse
    analyze_args = ["--ente", ente, "--base", resolved_base] + limit_args + llm_args
    steps.append((_module_command("delibere_comunali.parsing.analyze_albo", analyze_args), "Parsing/Analysis"))

    # Clean texts (optional)
    if not args.skip_clean:
        clean_args = ["--ente", ente, "--base", resolved_base]
        steps.append((_script_command("scripts/clean_texts.py", clean_args), "Text Cleaning"))

    # Post-process classification (optional)
    if not args.skip_post_process:
        post_proc_args = ["--ente", ente, "--base", resolved_base] + llm_args
        steps.append((_module_command("delibere_comunali.processing.post_process_classification", post_proc_args), "Post-Processing Classification"))

    # Knowledge Graph (optional)
    if not args.skip_kg:
        kg_args = ["--ente", ente, "--base", resolved_base]
        steps.append((_script_command("scripts/build_knowledge_graph.py", kg_args), "Knowledge Graph Building"))

    # ML Training (optional)
    train_args = ["--ente", ente, "--base", resolved_base] + llm_args
    steps.append((_script_command("scripts/train_model.py", train_args), "ML Model Training"))

    # Procedural Understanding (optional)
    if not args.skip_procedural:
        proc_args = ["--ente", ente, "--base", resolved_base]
        steps.append((_module_command("delibere_comunali.processing.procedural_understanding", proc_args), "Procedural Understanding Analysis"))

    # Audit (optional)
    if not args.only_analyze and not args.skip_audit:
        audit_args = ["--ente", ente, "--base", resolved_base] + llm_args
        steps.append((_module_command("delibere_comunali.processing.audit_engine", audit_args), "Audit Engine"))

    # Validation (optional)
    if not args.skip_validate:
        validate_args = ["--base", resolved_base]
        steps.append((_script_command("scripts/validate_output.py", validate_args), "Output Validation"))

    # Esegui tutti i passaggi pianificati
    for command, title in steps:
        run_step(command, title)

    # Fase di coordinamento centrale (se non saltata)
    if not args.skip_orchestration:
        print("\n" + "=" * 72)
        print("STEP: Coordinamento tra moduli avanzati")
        print("=" * 72)
        
        # Esegui l'orchestrator per coordinare i vari moduli
        orchestrator_args = ["--ente", ente, "--base-path", resolved_base]
        if args.skip_audit:
            orchestrator_args.append("--skip-audit")
        if args.skip_post_process:
            orchestrator_args.append("--skip-kpi")  # Considera che i KPI dipendono dal post-processing
        
        try:
            orchestrator_cmd = [sys.executable, "-m", "delibere_comunali.core.orchestrator"] + orchestrator_args
            result = subprocess.run(orchestrator_cmd, cwd=PROJECT_ROOT)
            if result.returncode != 0:
                print(f"⚠️  Orchestrator fallito, continuiamo comunque...")
            else:
                print("✅ Coordinamento tra moduli completato con successo")
        except Exception as e:
            print(f"⚠️  Errore nell'esecuzione dell'orchestrator: {e}")

    print("\n" + "=" * 72)
    print("PIPELINE COMPLETATO")
    print("=" * 72)

if __name__ == "__main__":
    main()