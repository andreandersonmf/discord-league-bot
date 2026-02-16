from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Boolean

from .session import Base

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, nullable=False)
    captain_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    players: Mapped[list["Player"]] = relationship(back_populates="team")

class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("guild_id", "user_id", name="uq_player_guild_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(String(128), nullable=False)

    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    team: Mapped["Team | None"] = relationship(back_populates="players")

class TransactionRequest(Base):
    __tablename__ = "transaction_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Quem pediu
    requested_by: Mapped[int] = mapped_column(Integer, nullable=False)

    # Jogador alvo
    target_user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_username: Mapped[str] = mapped_column(String(128), nullable=False)

    # Ação: ADD / REMOVE / TRANSFER
    action: Mapped[str] = mapped_column(String(16), nullable=False)

    # Times
    from_team_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    to_team_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING/APPROVED/REJECTED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    requested_role: Mapped[str | None] = mapped_column(String(24), nullable=True)

    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    player_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    player_confirmed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class MatchSchedule(Base):
    __tablename__ = "match_schedule"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False)

    match_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)  # tipo "SA-2026-0001"
    team_a: Mapped[str] = mapped_column(String(64), nullable=False)
    team_b: Mapped[str] = mapped_column(String(64), nullable=False)

    best_of: Mapped[int] = mapped_column(Integer, default=5)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="OPEN")  # OPEN/CLOSED/DONE
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MatchResult(Base):
    __tablename__ = "match_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(Integer, nullable=False)

    match_id: Mapped[str] = mapped_column(String(32), nullable=False)  # referencia schedule.match_id

    team_a_score: Mapped[int] = mapped_column(Integer, nullable=False)
    team_b_score: Mapped[int] = mapped_column(Integer, nullable=False)

    mvp_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mvp_b: Mapped[int | None] = mapped_column(Integer, nullable=True)

    posted_by: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)