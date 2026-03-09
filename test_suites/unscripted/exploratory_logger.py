"""
CSA Step 3 — Assurance Activity: Exploratory Logger (Unscripted Testing)

A CLI tool for capturing exploratory testing sessions.
Generates an immutable YAML log of actions, observations, and defects
to satisfy CSA Step 4 (Record) requirements for NOT HIGH risk features.
"""
import yaml
import os
import argparse
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from pydantic import BaseModel, Field
from typing import List, Optional

console = Console()

class LogEntry(BaseModel):
    timestamp: str
    type: str = Field(..., description="Action, Observation, or Defect")
    description: str
    severity: Optional[str] = None
    reproducibility: Optional[str] = None

class ExploratorySession(BaseModel):
    session_id: str
    feature_id: str
    name: str
    tester: str
    risk_level: str
    charter: str
    start_time: str
    end_time: Optional[str] = None
    logs: List[LogEntry] = []

def load_template(filepath: str) -> dict:
    if not os.path.exists(filepath):
        console.print(f"[bold red]Template file not found: {filepath}[/bold red]")
        exit(1)
    with open(filepath, "r") as f:
        return yaml.safe_load(f)

def run_session(template_path: str):
    data = load_template(template_path)
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    session = ExploratorySession(
        session_id=session_id,
        feature_id=data.get("feature_id", "UNKNOWN"),
        name=data.get("name", "Untitled Session"),
        tester=data.get("tester", "Unknown Tester"),
        risk_level=data.get("risk_level", "NOT HIGH"),
        charter=data.get("charter", ""),
        start_time=datetime.now().isoformat()
    )
    
    console.print(Panel.fit(
        f"[bold blue]Exploratory Session Started[/bold blue]\n"
        f"Feature: {session.feature_id} - {session.name}\n"
        f"Tester: {session.tester}\n"
        f"Charter: [italic]{session.charter}[/italic]",
        title=f"Session: {session_id}"
    ))
    
    console.print("[green]Available Commands:[/green]")
    console.print(" [bold A] - Log an Action")
    console.print(" [bold O] - Log an Observation")
    console.print(" [bold D] - Log a Defect")
    console.print(" [bold Q] - Quit and Save Session\n")
    
    try:
        while True:
            choice = Prompt.ask("Command [A/O/D/Q]", choices=["A", "a", "O", "o", "D", "d", "Q", "q"]).upper()
            
            if choice == "Q":
                break
                
            desc = Prompt.ask("Description")
            if not desc.strip():
                console.print("[yellow]Description cannot be empty.[/yellow]")
                continue
                
            log_type = {"A": "Action", "O": "Observation", "D": "Defect"}[choice]
            
            severity = None
            reproducibility = None
            
            if choice == "D":
                severity = Prompt.ask("Severity", choices=["Critical", "Major", "Minor", "Cosmetic"])
                reproducibility = Prompt.ask("Reproducibility", choices=["Always", "Sometimes", "Once"])
            
            entry = LogEntry(
                timestamp=datetime.now().isoformat(),
                type=log_type,
                description=desc,
                severity=severity,
                reproducibility=reproducibility
            )
            session.logs.append(entry)
            
            color = {"Action": "cyan", "Observation": "green", "Defect": "red"}[log_type]
            console.print(f"[{color}]* {log_type} recorded.[/{color}]\n")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Session interrupted.[/yellow]")
        
    session.end_time = datetime.now().isoformat()
    
    # Save the session
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sessions_dir = os.path.join(base_dir, "sessions")
    
    # Ensure directory exists (we handle this in python rather than bash now)
    os.makedirs(sessions_dir, exist_ok=True)
        
    output_file = os.path.join(sessions_dir, f"{session_id}_{session.feature_id}.yaml")
    
    with open(output_file, "w") as f:
        yaml.dump(session.model_dump(), f, sort_keys=False)
        
    console.print(Panel.fit(
        f"[bold green]Session Saved Successfully[/bold green]\n"
        f"File: {output_file}\n"
        f"Total Logs: {len(session.logs)}",
        title="Session Completed"
    ))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exploratory Testing Session Logger")
    parser.add_argument("--template", required=True, help="Path to the session template YAML")
    args = parser.parse_args()
    
    run_session(args.template)
