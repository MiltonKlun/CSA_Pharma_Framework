"""
CSA Step 4 — Record: Audit Trail Collector
Extracts raw compliance logs from the system database into immutable JSON evidence.
"""
import sqlite3
import json
import os
import getpass
import platform
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from evidence_capture.integrity import write_sha256_sidecar

console = Console()

def collect_audit_trail(db_path: str = "demo.db", output_dir: str = "evidence_capture"):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(db_path):
        console.print(f"[bold red]Database not found at {db_path}[/bold red]")
        console.print("Please ensure the demo app has been seeded with data first.")
        return None
        
    output_file = os.path.join(output_dir, "extracted_audit_trail.json")
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query all audit trail records, ordering by ID to ensure sequence
        cursor.execute("SELECT * FROM audit_trail ORDER BY id ASC")
        rows = cursor.fetchall()
        
        records = [dict(row) for row in rows]
        
        evidence = {
            "metadata": {
                "extracted_at": datetime.now().isoformat(),
                "extracted_by": getpass.getuser(),
                "hostname": platform.node(),
                "source_db": db_path,
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
            f"Source: {db_path}\n"
            f"Records captured: {len(records)}\n"
            f"Evidence File: {output_file}\n"
            f"SHA-256: [dim]{digest[:16]}...{digest[-8:]}[/dim]",
            title="CSA Audit Trail Collector"
        ))
        
        return output_file
        
    except sqlite3.Error as e:
        console.print(f"[bold red]Database Error:[/bold red] {e}")
        return None
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    console.print("[cyan]Initializing Evidence Collection...[/cyan]")
    # Looking for pharma_qms.db in the app root
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pharma_qms.db")
    result = collect_audit_trail(db_path)
    
    if not result:
        import sys
        sys.exit(1)
