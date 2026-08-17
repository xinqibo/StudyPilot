from __future__ import annotations

from sqlalchemy import Boolean,ForeignKey,Integer,JSON,String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base



class LearningPlanDB(Base):
    __tablename__ = "learning_plan"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    goal: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    current_level: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    duration_weeks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    minutes_per_day: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    weekly_objectives: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )

    tasks:Mapped[list[LearningTaskDB]] = relationship(
        back_populates="plan",
        cascade="all,delete-orphan",
    )


class LearningTaskDB(Base):
    __tablename__ = "learning_task"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("learning_plan.id"),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    estimated_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    acceptance_criteria:Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
    )

    completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    plan: Mapped[LearningPlanDB] = relationship(
        back_populates="tasks",
    )