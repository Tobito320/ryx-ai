"""
Reminder System for RyxHub
Tracks appointments, deadlines, and events
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum


DATA_DIR = Path(__file__).parent.parent / "data"
REMINDERS_FILE = DATA_DIR / "reminders.json"


class ReminderStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class ReminderType(str, Enum):
    APPOINTMENT = "appointment"
    DEADLINE = "deadline"
    TRASH = "trash"
    BILL = "bill"
    EVENT = "event"
    CUSTOM = "custom"


class Reminder(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    type: ReminderType = ReminderType.CUSTOM
    date: str  # ISO format
    time: Optional[str] = None  # HH:MM
    status: ReminderStatus = ReminderStatus.PENDING
    source: Optional[str] = None  # Where this came from (email, document, manual)
    source_id: Optional[str] = None  # Link to source document/email
    notes: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None
    auto_delete_days: int = 7  # Delete after X days past due


class ReminderSystem:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.reminders: List[Reminder] = []
        self.load()
    
    def load(self):
        """Load reminders from disk"""
        if REMINDERS_FILE.exists():
            try:
                with open(REMINDERS_FILE, "r") as f:
                    data = json.load(f)
                    self.reminders = [Reminder(**r) for r in data]
            except Exception:
                self.reminders = []
    
    def save(self):
        """Save reminders to disk"""
        with open(REMINDERS_FILE, "w") as f:
            json.dump([r.model_dump() for r in self.reminders], f, indent=2, default=str)
    
    def add_reminder(
        self,
        title: str,
        date: str,
        type: ReminderType = ReminderType.CUSTOM,
        time: str = None,
        description: str = None,
        source: str = None,
        source_id: str = None,
    ) -> Reminder:
        """Add a new reminder"""
        reminder = Reminder(
            id=f"rem_{len(self.reminders)}_{datetime.now().timestamp()}",
            title=title,
            description=description,
            type=type,
            date=date,
            time=time,
            source=source,
            source_id=source_id,
            created_at=datetime.now().isoformat(),
        )
        self.reminders.append(reminder)
        self.save()
        return reminder
    
    def get_upcoming(self, days: int = 7) -> List[Reminder]:
        """Get upcoming reminders for the next X days"""
        today = datetime.now().date()
        future = today + timedelta(days=days)
        
        upcoming = []
        for r in self.reminders:
            if r.status != ReminderStatus.PENDING:
                continue
            try:
                reminder_date = datetime.fromisoformat(r.date).date()
                if today <= reminder_date <= future:
                    upcoming.append(r)
            except Exception:
                pass
        
        return sorted(upcoming, key=lambda r: r.date)
    
    def get_today(self) -> List[Reminder]:
        """Get today's reminders"""
        today = datetime.now().date().isoformat()
        return [
            r for r in self.reminders
            if r.date.startswith(today) and r.status == ReminderStatus.PENDING
        ]
    
    def get_overdue(self) -> List[Reminder]:
        """Get overdue reminders"""
        today = datetime.now().date()
        overdue = []
        for r in self.reminders:
            if r.status != ReminderStatus.PENDING:
                continue
            try:
                reminder_date = datetime.fromisoformat(r.date).date()
                if reminder_date < today:
                    overdue.append(r)
            except Exception:
                pass
        return sorted(overdue, key=lambda r: r.date)
    
    def update_status(
        self,
        reminder_id: str,
        status: ReminderStatus,
        notes: str = None
    ) -> Optional[Reminder]:
        """Update reminder status"""
        for r in self.reminders:
            if r.id == reminder_id:
                r.status = status
                if notes:
                    r.notes = notes
                if status in [ReminderStatus.COMPLETED, ReminderStatus.MISSED, ReminderStatus.CANCELLED]:
                    r.completed_at = datetime.now().isoformat()
                self.save()
                return r
        return None
    
    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder"""
        for i, r in enumerate(self.reminders):
            if r.id == reminder_id:
                self.reminders.pop(i)
                self.save()
                return True
        return False
    
    def cleanup_old(self):
        """Remove old completed/missed reminders past auto_delete_days"""
        now = datetime.now()
        to_keep = []
        
        for r in self.reminders:
            if r.status == ReminderStatus.PENDING:
                to_keep.append(r)
                continue
            
            if r.completed_at:
                try:
                    completed = datetime.fromisoformat(r.completed_at)
                    if (now - completed).days <= r.auto_delete_days:
                        to_keep.append(r)
                except Exception:
                    to_keep.append(r)
            else:
                to_keep.append(r)
        
        if len(to_keep) != len(self.reminders):
            self.reminders = to_keep
            self.save()
    
    def get_by_source(self, source_id: str) -> List[Reminder]:
        """Get reminders linked to a specific source (document/email)"""
        return [r for r in self.reminders if r.source_id == source_id]


# Singleton instance
reminder_system = ReminderSystem()
