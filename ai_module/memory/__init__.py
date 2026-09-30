"""
ai_module.memory
----------------
Persistent task and meeting memory layer.

Exports:
    TaskMemory          – canonical multi-meeting task store with stable IDs
    MeetingMemory       – per-meeting record store
    TaskRepository      – abstract repository interface
    InMemoryTaskRepository   – in-memory repository
    JsonFileTaskRepository   – JSON file-backed repository
    InMemoryMeetingRepository – in-memory meeting repository
"""

from ai_module.memory.task_memory import TaskMemory
from ai_module.memory.meeting_memory import MeetingMemory
from ai_module.memory.repository import (
    TaskRepository,
    InMemoryTaskRepository,
    JsonFileTaskRepository,
    InMemoryMeetingRepository,
)

__all__ = [
    "TaskMemory",
    "MeetingMemory",
    "TaskRepository",
    "InMemoryTaskRepository",
    "JsonFileTaskRepository",
    "InMemoryMeetingRepository",
]
