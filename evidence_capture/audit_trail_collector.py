"""
CSA Step 4 — Record: Audit Trail Collector
Extracts raw compliance logs from the system database into immutable JSON evidence.
"""
import os
import json
import getpass
import platform
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from evidence_capture.integrity import write_sha256_sidecar
import sys

# Add the project root to sys.path if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_app.app.database import SessionLocal, engine
from demo_app.app.models import AuditTrail

console = Console()

def collect_audit_trail(output_dir: str = "evidence_capture"):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    db_source = str(engine.url)
    console.print(f"[dim]Connecting to database: {db_source}[/dim]")
    
    output_file = os.path.join(output_dir, "extracted_audit_trail.json")
    
    db = SessionLocal()
    try:
        # Query all audit trail records, ordering by ID to ensure sequence
        audits = db.query(AuditTrail).order_by(AuditTrail.id.asc()).all()
        
        # Convert SQLAlchemy objects to dicts
        records = []
        for a in audits:
            record = {
                "id": a.id,
                "user_id": a.user_id,
                "action": a.action,
                "table_name": a.table_name,
                "record_id": a.record_id,
                "old_values": a.old_values,
                "new_values": a.new_values,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None
            }
            records.append(record)
        
        evidence = {
            "metadata": {
                "extracted_at": datetime.now().isoformat(),
                "extracted_by": getpass.getuser(),
                "hostname": platform.node(),
                "source_db": db_source,
                "total_records": len(records)
            },
            "records": records
        }
        
        with open(output_file, "w") as f:
            json.dump(evidence, f, indent=2)
            
        # Write SHA-256 sidecar for integrity verification (PIC/S PI 041 §6.9)
        digest = write_sha256_sidecar(output_file)
            
        console.print(Panel.fit(
            f"[bold green]Data Extracted Successfully[/bold green]\n"
            f"Extracted by: {getpass.getuser()} @ {platform.node()}\n"
            f"Source: {db_source}\n"
            f"Records captured: {len(records)}\n"
            f"Evidence File: {output_file}\n"
            f"SHA-256: [dim]{digest[:16]}...{digest[-8:]}[/dim]",
            title="CSA Audit Trail Collector"
        ))
        
        return output_file
        
    except Exception as e:
        console.print(f"[bold red]Database Error:[/bold red] {e}")
        return None
    finally:
        db.close()

if __name__ == "__main__":
    console.print("[cyan]Initializing Evidence Collection...[/cyan]")
    result = collect_audit_trail()
    
    if not result:
        import sys
        sys.exit(1)
