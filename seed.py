"""Seed script — wipes all data and loads realistic demo data."""
import datetime
from sqlalchemy.orm import Session
from database import (
    engine, Base,
    CommissionBracket, Employee, CommissionCycle,
    Project, ProjectAssignment, Collection, EmployeePayment,
)

def run():
    with Session(engine) as s:
        # ── Wipe everything except brackets ──────────────────────────────
        s.query(EmployeePayment).delete()
        s.query(Collection).delete()
        s.query(ProjectAssignment).delete()
        s.query(CommissionCycle).delete()
        s.query(Employee).delete()
        s.query(Project).delete()
        s.commit()

        # ── 5 Employees ───────────────────────────────────────────────────
        alice = Employee(name="Alice Chen",    employment_date=datetime.date(2022, 3, 1),  gender="female")
        bob   = Employee(name="Bob Martinez",  employment_date=datetime.date(2021, 8, 15), gender="male")
        carol = Employee(name="Carol Kim",     employment_date=datetime.date(2023, 1, 10), gender="female")
        david = Employee(name="David Nguyen",  employment_date=datetime.date(2022, 6, 1),  gender="male")
        emma  = Employee(name="Emma Patel",    employment_date=datetime.date(2023, 5, 20), gender="female")
        for emp in [alice, bob, carol, david, emma]:
            s.add(emp)
        s.flush()

        # Commission cycles (threshold $20k, no carryforward)
        for emp, thresh, carry in [
            (alice, 20000, 0),
            (bob,   20000, 5000),
            (carol, 15000, 0),
            (david, 20000, 0),
            (emma,  10000, 0),
        ]:
            s.add(CommissionCycle(
                employee_id=emp.id,
                start_date=emp.employment_date,
                end_date=None,
                applicable_threshold=thresh,
                threshold_carryforward=carry,
            ))

        # ── 3 Projects ────────────────────────────────────────────────────
        p1 = Project(customer="Greenfield Solar LLC",
                     project_no="DVT-2024-001",
                     description="Rooftop solar + battery install",
                     contract_amount=1_800_000)
        p2 = Project(customer="Metro EV Charging Co.",
                     project_no="DVT-2024-002",
                     description="EV charging station network",
                     contract_amount=3_200_000)
        p3 = Project(customer="Pacific Industrial Group",
                     project_no="DVT-2024-003",
                     description="Industrial power upgrade",
                     contract_amount=950_000)
        for p in [p1, p2, p3]:
            s.add(p)
        s.flush()

        # ── Team assignments ──────────────────────────────────────────────
        # Project 1: Alice 60%, Bob 40%
        s.add(ProjectAssignment(project_id=p1.id, employee_id=alice.id, distribution=0.60))
        s.add(ProjectAssignment(project_id=p1.id, employee_id=bob.id,   distribution=0.40))

        # Project 2: Alice 30%, Carol 40%, David 30%
        s.add(ProjectAssignment(project_id=p2.id, employee_id=alice.id, distribution=0.30))
        s.add(ProjectAssignment(project_id=p2.id, employee_id=carol.id, distribution=0.40))
        s.add(ProjectAssignment(project_id=p2.id, employee_id=david.id, distribution=0.30))

        # Project 3: Bob 50%, Emma 50%
        s.add(ProjectAssignment(project_id=p3.id, employee_id=bob.id,  distribution=0.50))
        s.add(ProjectAssignment(project_id=p3.id, employee_id=emma.id, distribution=0.50))

        # ── Collections ───────────────────────────────────────────────────
        def col(project, date, amount, tax=0, ref=0, exp=0):
            s.add(Collection(
                project_id=project.id,
                collection_date=datetime.date.fromisoformat(date),
                collection_amount=amount,
                sales_tax=tax, referral_fee=ref, approved_sales_exp=exp,
            ))

        # Project 1 — Greenfield Solar (contract $1.8M)
        col(p1, "2024-02-15",  250_000, tax=18_500, ref=5_000)
        col(p1, "2024-04-10",  320_000, tax=23_680, ref=5_000, exp=2_000)
        col(p1, "2024-07-01",  400_000, tax=29_600, ref=8_000)
        col(p1, "2024-09-20",  380_000, tax=28_120, ref=8_000, exp=3_500)
        col(p1, "2024-11-30",  290_000, tax=21_460, ref=5_000)

        # Project 2 — Metro EV (contract $3.2M)
        col(p2, "2024-01-20",  400_000, tax=29_600)
        col(p2, "2024-03-05",  550_000, tax=40_700, ref=10_000)
        col(p2, "2024-05-18",  680_000, tax=50_320, ref=12_000, exp=5_000)
        col(p2, "2024-08-12",  720_000, tax=53_280, ref=15_000, exp=8_000)
        col(p2, "2024-10-25",  490_000, tax=36_260, ref=10_000)

        # Project 3 — Pacific Industrial (contract $950k)
        col(p3, "2024-03-22",  180_000, tax=13_320, ref=3_500)
        col(p3, "2024-06-14",  240_000, tax=17_760, ref=5_000, exp=1_500)
        col(p3, "2024-09-05",  310_000, tax=22_940, ref=6_000, exp=2_000)

        # ── Employee payments ─────────────────────────────────────────────
        def pay(emp, date, amount, note=None):
            s.add(EmployeePayment(
                employee_id=emp.id,
                payment_date=datetime.date.fromisoformat(date),
                amount=amount,
                note=note,
            ))

        pay(alice, "2024-05-01", 8_000,  "advance Q2")
        pay(alice, "2024-08-15", 12_000, "settlement Q3")
        pay(bob,   "2024-06-01", 5_000,  "advance")
        pay(bob,   "2024-11-01", 9_500,  "settlement Q4")
        pay(carol, "2024-07-15", 6_000,  "advance Q3")
        pay(david, "2024-09-30", 7_200,  "settlement")
        pay(emma,  "2024-10-10", 3_500,  "advance")

        s.commit()
        print("✓ Seed complete.")
        print(f"  Projects : {s.query(Project).count()}")
        print(f"  Employees: {s.query(Employee).count()}")
        print(f"  Collections: {s.query(Collection).count()}")
        print(f"  Payments: {s.query(EmployeePayment).count()}")

if __name__ == "__main__":
    run()
