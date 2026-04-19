"""bookgen CLI — job management for the Book Generation Engine."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="bookgen", help="Book Generation Engine CLI")
console = Console()

BOOKGEN_API_URL: str = os.getenv("BOOKGEN_API_URL", "http://localhost:8000")


def _client() -> httpx.Client:
    return httpx.Client(base_url=BOOKGEN_API_URL, timeout=30.0)


def _handle_error(response: httpx.Response, action: str) -> None:
    """Print error detail and exit 1."""
    try:
        detail = response.json().get("detail", response.text)
    except Exception:
        detail = response.text
    console.print(f"[red]Error {action}: {response.status_code} — {detail}[/red]")
    raise typer.Exit(code=1)


@app.command()
def submit(
    config: Path = typer.Option(..., "--config", "-c", help="Path to JSON job config file"),
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Notification email"),
):
    """Submit a new book generation job."""
    if not config.exists():
        console.print(f"[red]Config file not found: {config}[/red]")
        raise typer.Exit(code=1)

    job_config = json.loads(config.read_text())
    payload: dict = {"config": job_config, "status": "queued"}
    if email:
        payload["notification_email"] = email

    try:
        with _client() as client:
            resp = client.post("/jobs", json=payload)
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to API at {BOOKGEN_API_URL}[/red]")
        raise typer.Exit(code=1)

    if resp.status_code not in (200, 201):
        _handle_error(resp, "submitting job")

    job_id = resp.json().get("id") or resp.json().get("job_id", "unknown")
    console.print(f"[green]Job submitted:[/green] {job_id}")


@app.command("list")
def list_jobs(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results"),
):
    """List book generation jobs."""
    params: dict = {"limit": limit}
    if status:
        params["status"] = status

    try:
        with _client() as client:
            resp = client.get("/jobs", params=params)
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to API at {BOOKGEN_API_URL}[/red]")
        raise typer.Exit(code=1)

    if resp.status_code != 200:
        _handle_error(resp, "listing jobs")

    data = resp.json()
    jobs = data.get("jobs", [])

    table = Table(title=f"Jobs (total: {data.get('total', len(jobs))})")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Created At")

    for job in jobs:
        table.add_row(job["id"], job["status"], job.get("created_at", ""))

    console.print(table)


@app.command()
def cancel(job_id: str = typer.Argument(..., help="Job UUID to cancel")):
    """Cancel a running job."""
    try:
        with _client() as client:
            resp = client.delete(f"/jobs/{job_id}")
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to API at {BOOKGEN_API_URL}[/red]")
        raise typer.Exit(code=1)

    if resp.status_code != 204:
        _handle_error(resp, "cancelling job")

    console.print(f"[green]Job {job_id} cancelled.[/green]")


@app.command()
def restart(job_id: str = typer.Argument(..., help="Job UUID to restart")):
    """Restart a failed or cancelled job."""
    try:
        with _client() as client:
            resp = client.post(f"/jobs/{job_id}/restart")
    except httpx.ConnectError:
        console.print(f"[red]Cannot connect to API at {BOOKGEN_API_URL}[/red]")
        raise typer.Exit(code=1)

    if resp.status_code != 201:
        _handle_error(resp, "restarting job")

    new_id = resp.json().get("new_job_id", "unknown")
    console.print(f"[green]Job restarted. New job ID:[/green] {new_id}")


@app.command()
def batch(
    file: Path = typer.Option(..., "--file", "-f", help="Path to JSON or CSV file"),
):
    """Submit a batch of jobs from a JSON or CSV file."""
    if not file.exists():
        console.print(f"[red]Batch file not found: {file}[/red]")
        raise typer.Exit(code=1)

    suffix = file.suffix.lower()
    if suffix == ".json":
        jobs = json.loads(file.read_text())
        payload = {"format": "json", "jobs": jobs if isinstance(jobs, list) else [jobs]}
        try:
            with _client() as client:
                resp = client.post("/batch", json=payload)
        except httpx.ConnectError:
            console.print(f"[red]Cannot connect to API at {BOOKGEN_API_URL}[/red]")
            raise typer.Exit(code=1)
    elif suffix == ".csv":
        try:
            with _client() as client:
                resp = client.post(
                    "/batch/csv",
                    files={"file": (file.name, file.read_bytes(), "text/csv")},
                )
        except httpx.ConnectError:
            console.print(f"[red]Cannot connect to API at {BOOKGEN_API_URL}[/red]")
            raise typer.Exit(code=1)
    else:
        console.print(f"[red]Unsupported file format: {suffix}. Use .json or .csv[/red]")
        raise typer.Exit(code=1)

    if resp.status_code not in (200, 201):
        _handle_error(resp, "submitting batch")

    data = resp.json()
    console.print(f"[green]Batch submitted.[/green] ID: {data['batch_id']}")
    console.print(f"  Enqueued: {data['enqueued']}, Skipped: {data['skipped']}")
    if data.get("errors"):
        console.print(f"  [yellow]Errors on rows: {[e['row'] for e in data['errors']]}[/yellow]")


if __name__ == "__main__":
    app()
