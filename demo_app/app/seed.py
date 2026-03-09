import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base, SessionLocal
from app.models import User, UserRole, Document, DocumentStatus, Deviation, DeviationStatus
from app.routes.auth import get_password_hash
from app.audit_trail import current_user_id_ctx

def seed_database():
    print("Initializing Database schema...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Seeding Users...")
        
        # Set a system context ID for the creation of the initial users
        current_user_id_ctx.set(1)
        
        operator1 = User(
            username="operator1",
            email="operator1@pharma.local",
            full_name="John Operator",
            hashed_password=get_password_hash("Op3rator!23"),
            role=UserRole.OPERATOR
        )
        
        qa1 = User(
            username="qa1",
            email="qa1@pharma.local",
            full_name="Alice QA",
            hashed_password=get_password_hash("Qa!2345678"),
            role=UserRole.QA
        )
        
        manager1 = User(
            username="manager1",
            email="manager1@pharma.local",
            full_name="Bob Manager",
            hashed_password=get_password_hash("Manager!23"),
            role=UserRole.MANAGER
        )
        
        admin1 = User(
            username="admin1",
            email="admin1@pharma.local",
            full_name="System Admin",
            hashed_password=get_password_hash("Admin!2345"),
            role=UserRole.ADMIN
        )
        
        db.add_all([operator1, qa1, manager1, admin1])
        db.commit()
        
        print(f"Users seeded: {operator1.username}, {qa1.username}, {manager1.username}, {admin1.username}")
        
        print("Seeding sample documents...")
        doc1 = Document(
            title="SOP-001: General Good Manufacturing Practices",
            content="Maintain hygiene, wear PPE, document everything...",
            version="1.0",
            status=DocumentStatus.APPROVED,
            author_id=manager1.id,
            approver_id=qa1.id
        )
        db.add(doc1)
        db.commit()
        
        print("Seeding sample deviation...")
        dev1 = Deviation(
            title="DEV-2026-001: Temperature excursion in Cold Room A",
            description="Temperature dropped below threshold (1.5C) for 15 minutes.",
            status=DeviationStatus.OPEN,
            reported_by_id=operator1.id
        )
        db.add(dev1)
        db.commit()
        
        print("Database seeded successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
