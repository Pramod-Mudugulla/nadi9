import argparse
import json
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from src.nadi9.graph.workflow import NadiWorkflow
from src.nadi9.providers.mock import MockLLMProvider
from src.nadi9.providers.llm import LiveLLMProvider
from src.nadi9.retrieval.retriever import EvidenceRetriever

console = Console()


def run_pipeline(provider_mode: str = "mock") -> None:
    console.print(Panel.fit("[bold cyan]Nadi-9 Dialect Agent Pipeline[/bold cyan]\nEvidence-grounded learning and subtitle verification"))

    provider = MockLLMProvider() if provider_mode == "mock" else LiveLLMProvider()
    retriever = EvidenceRetriever()
    workflow = NadiWorkflow(provider=provider, retriever=retriever)

    state = workflow.run_pipeline()

    # Display Results Table
    table = Table(title=f"Episode {state.episode_id} Subtitle Decisions")
    table.add_column("ID", style="bold")
    table.add_column("Source Text", max_width=30)
    table.add_column("Nadi-9 Translation", max_width=30)
    table.add_column("Conf.", justify="right")
    table.add_column("Decision", style="bold")
    table.add_column("Review Question", max_width=35)

    for sub_id, d in state.subtitle_decisions.items():
        decision_color = "[green]PASS[/green]" if d.decision == "PASS" else "[yellow]HUMAN_REVIEW[/yellow]"
        table.add_row(
            sub_id,
            d.source_text,
            d.nadi_9_text,
            f"{d.confidence:.2f}",
            decision_color,
            d.review_question or "-",
        )

    console.print(table)

    # Export sample_run artifacts
    workflow.export_srt(state)
    workflow.export_decisions_jsonl(state)
    workflow.export_learned_rules(state)
    workflow.export_review_queue(state)
    workflow.export_final_report(state)

    console.print(f"\n[green]Artifacts successfully written to sample_run/[/green]")
    console.print(f"- Subtitles SRT: [cyan]sample_run/subtitles.srt[/cyan]")
    console.print(f"- Decision JSONL: [cyan]sample_run/subtitle_decisions.jsonl[/cyan]")
    console.print(f"- Review Queue: [cyan]sample_run/review_queue.json[/cyan]")
    console.print(f"- Learned Rules: [cyan]sample_run/learned_rules.json[/cyan]")
    console.print(f"- Final Report: [cyan]sample_run/final_report.md[/cyan]")


def apply_correction() -> None:
    console.print("[bold yellow]Testing Selective Replanning on Correction Event...[/bold yellow]")
    provider = MockLLMProvider()
    retriever = EvidenceRetriever()
    workflow = NadiWorkflow(provider=provider, retriever=retriever)

    # Initial run
    state = workflow.run_pipeline()
    console.print(f"Pre-correction S014 decision: [yellow]{state.subtitle_decisions['S014'].decision}[/yellow] - '{state.subtitle_decisions['S014'].nadi_9_text}'")

    # Apply correction
    reprocessed = workflow.apply_correction("data/scenarios/linguist_correction.json", state)
    console.print(f"[green]Selectively reprocessed {len(reprocessed)} subtitle(s): {reprocessed}[/green]")
    console.print(f"Post-correction S014 decision: [green]{state.subtitle_decisions['S014'].decision}[/green] - '{state.subtitle_decisions['S014'].nadi_9_text}'")

    # Re-export
    workflow.export_decisions_jsonl(state)
    workflow.export_review_queue(state)
    workflow.export_srt(state)


def inspect_subtitle(sub_id: str) -> None:
    retriever = EvidenceRetriever()
    workflow = NadiWorkflow(retriever=retriever)
    state = workflow.run_pipeline()

    if sub_id not in state.subtitle_decisions:
        console.print(f"[red]Subtitle ID {sub_id} not found.[/red]")
        return

    d = state.subtitle_decisions[sub_id]
    console.print(Panel(f"""
[bold]Subtitle ID:[/bold] {d.subtitle_id}
[bold]Source Text:[/bold] {d.source_text}
[bold]Nadi-9 Translation:[/bold] {d.nadi_9_text}
[bold]Confidence:[/bold] {d.confidence} ({d.confidence_reason})
[bold]Decision:[/bold] {d.decision}
[bold]Evidence References:[/bold] {d.evidence}
[bold]Assumptions:[/bold] {d.assumptions}
[bold]Conflicts:[/bold] {d.conflicts}
[bold]Review Question:[/bold] {d.review_question}
[bold]Timing & Speed:[/bold] {d.time_in} -> {d.time_out} ({d.reading_speed_cps} CPS)
[bold]Verification Notes:[/bold] {d.verification_notes}
    """, title=f"Full Audit Trail: {sub_id}"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Nadi-9 Dialect Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    run_parser = subparsers.add_parser("run", help="Run full pipeline")
    run_parser.add_argument("--provider", default="mock", choices=["mock", "live"], help="LLM Provider")

    subparsers.add_parser("correct", help="Test selective correction replanning")

    inspect_parser = subparsers.add_parser("inspect", help="Inspect decision audit trail")
    inspect_parser.add_argument("subtitle_id", help="e.g. S014 or S008")

    args = parser.parse_args()

    if args.command == "run" or args.command is None:
        run_pipeline(getattr(args, "provider", "mock"))
    elif args.command == "correct":
        apply_correction()
    elif args.command == "inspect":
        inspect_subtitle(args.subtitle_id)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
