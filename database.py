from __future__ import annotations

import datetime
from typing import Optional

from sqlalchemy import Date, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

DATABASE_URL = "sqlite:///commission.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


class Base(DeclarativeBase):
    pass


class CommissionBracket(Base):
    __tablename__ = "commission_brackets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upper_bound: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # None = infinity
    rate: Mapped[float] = mapped_column(Float, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    employment_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)

    cycles: Mapped[list[CommissionCycle]] = relationship("CommissionCycle", back_populates="employee")
    assignments: Mapped[list[ProjectAssignment]] = relationship("ProjectAssignment", back_populates="employee")
    payments: Mapped[list[EmployeePayment]] = relationship(
        "EmployeePayment", back_populates="employee",
        order_by="EmployeePayment.payment_date",
    )


class CommissionCycle(Base):
    __tablename__ = "commission_cycles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    start_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    applicable_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=20000.0)
    threshold_carryforward: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    employee: Mapped[Employee] = relationship("Employee", back_populates="cycles")

    @property
    def commission_threshold(self) -> float:
        return max(0.0, self.applicable_threshold - self.threshold_carryforward)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    project_no: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contract_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    assignments: Mapped[list[ProjectAssignment]] = relationship(
        "ProjectAssignment", back_populates="project", cascade="all, delete-orphan"
    )
    collections: Mapped[list[Collection]] = relationship(
        "Collection", back_populates="project", cascade="all, delete-orphan",
        order_by="Collection.collection_date, Collection.id",
    )


class ProjectAssignment(Base):
    __tablename__ = "project_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    distribution: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)  # 0.0–1.0

    project: Mapped[Project] = relationship("Project", back_populates="assignments")
    employee: Mapped[Employee] = relationship("Employee", back_populates="assignments")


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    collection_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    collection_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    sales_tax: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    referral_fee: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    approved_sales_exp: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    project: Mapped[Project] = relationship("Project", back_populates="collections")


class EmployeePayment(Base):
    __tablename__ = "employee_payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payment_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    employee: Mapped[Employee] = relationship("Employee", back_populates="payments")


DEFAULT_BRACKETS = [
    {"upper_bound": 1_000_000, "rate": 0.02, "sort_order": 0},
    {"upper_bound": 3_000_000, "rate": 0.03, "sort_order": 1},
    {"upper_bound": 7_000_000, "rate": 0.04, "sort_order": 2},
    {"upper_bound": None,      "rate": 0.05, "sort_order": 3},
]


def init_db() -> None:
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        if session.query(CommissionBracket).count() == 0:
            for b in DEFAULT_BRACKETS:
                session.add(CommissionBracket(**b))
            session.commit()


def get_session() -> Session:
    return Session(engine)
