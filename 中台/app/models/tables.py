from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TaskRoute(Base):
    __tablename__ = "task_route"

    id: Mapped[int] = mapped_column(primary_key=True)
    handler_name: Mapped[str] = mapped_column(String)
    feishu_table_id: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String)  # dingtalk / wecom / both
    group_id: Mapped[str] = mapped_column(String)  # 默认目标群 ID
    field_mapping: Mapped[str] = mapped_column(Text, nullable=True)  # JSONB as Text for SQLite
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaskInstance(Base):
    __tablename__ = "task_instance"

    id: Mapped[int] = mapped_column(primary_key=True)
    handler_name: Mapped[str] = mapped_column(String)
    route_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_route.id"), nullable=True)
    feishu_record_id: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String)  # dingtalk / wecom
    group_id: Mapped[str] = mapped_column(String)  # 实际发送的群
    card_id: Mapped[str] = mapped_column(String, nullable=True)  # 互动卡片 ID
    status: Mapped[str] = mapped_column(String)  # 任务级状态
    flow_state: Mapped[str] = mapped_column(Text, nullable=True)  # JSONB as Text for SQLite
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TaskParticipant(Base):
    __tablename__ = "task_participant"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_instance.id"))
    feishu_user_id: Mapped[str] = mapped_column(String)
    platform_user_id: Mapped[str] = mapped_column(String, nullable=True)  # 钉钉/企微用户 ID
    role: Mapped[str] = mapped_column(String)  # 创建者/执行者/评审者
    status: Mapped[str] = mapped_column(String)  # pending/confirmed/submitted/completed
    file_count: Mapped[int] = mapped_column(Integer, default=0)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FileRecord(Base):
    __tablename__ = "file_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_instance.id"))
    participant_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_participant.id"))
    file_url: Mapped[str] = mapped_column(String)
    file_name: Mapped[str] = mapped_column(String)
    file_type: Mapped[str] = mapped_column(String)  # image/document/video
    platform_msg_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReminderLog(Base):
    __tablename__ = "reminder_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_instance.id"))
    participant_id: Mapped[int] = mapped_column(Integer, ForeignKey("task_participant.id"))
    remind_type: Mapped[str] = mapped_column(String)  # private/group/escalation
    remind_count: Mapped[int] = mapped_column(Integer, default=0)
    next_remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class UserMapping(Base):
    __tablename__ = "user_mapping"

    id: Mapped[int] = mapped_column(primary_key=True)
    feishu_user_id: Mapped[str] = mapped_column(String, nullable=True)
    dingtalk_user_id: Mapped[str] = mapped_column(String, nullable=True)
    wecom_user_id: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str] = mapped_column(String, nullable=True)  # 手机号（匹配用）
    name: Mapped[str] = mapped_column(String, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupMapping(Base):
    __tablename__ = "group_mapping"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    group_id: Mapped[str] = mapped_column(String)
    platform: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RDTask(Base):
    __tablename__ = "rd_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_by: Mapped[str] = mapped_column(String, nullable=True)
    template_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("pipeline_template.id"), nullable=True)
    stages_snapshot: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sub_tasks: Mapped[list["RDSubTask"]] = relationship(back_populates="rd_task", cascade="all, delete-orphan")


class RDSubTask(Base):
    __tablename__ = "rd_sub_task"

    id: Mapped[int] = mapped_column(primary_key=True)
    rd_task_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("rd_task.id", ondelete="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    assignees: Mapped[str] = mapped_column(Text, default="[]")
    group_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, default="")
    platform: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="")
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    deliverables: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    task_instance_id: Mapped[int] = mapped_column(Integer, nullable=True, index=True)
    task_route_id: Mapped[int] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    project_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("rd_project.id", ondelete="SET NULL"), nullable=True, index=True)
    stage_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    stage_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    rd_task: Mapped[Optional["RDTask"]] = relationship(back_populates="sub_tasks")
    project: Mapped[Optional["RDProject"]] = relationship(back_populates="sub_tasks", foreign_keys=[project_id])


class PipelineTemplate(Base):
    __tablename__ = "pipeline_template"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    stages: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RDProject(Base):
    __tablename__ = "rd_project"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, nullable=True)
    template_id: Mapped[int] = mapped_column(Integer, ForeignKey("pipeline_template.id"), nullable=True)
    stages_snapshot: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    sub_tasks: Mapped[list["RDSubTask"]] = relationship(
        back_populates="project",
        foreign_keys="RDSubTask.project_id",
        cascade="all, delete-orphan",
    )
