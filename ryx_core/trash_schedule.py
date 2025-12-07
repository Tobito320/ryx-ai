"""
Trash Schedule Integration for Hagen (HEB)
Downloads and parses ICS calendar for Alleestraße 58
"""

import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import urllib.request
import ssl
from dataclasses import dataclass


DATA_DIR = Path(__file__).parent.parent / "data"
TRASH_CACHE_FILE = DATA_DIR / "trash_schedule.json"
TRASH_CONFIG_FILE = DATA_DIR / "trash_config.json"


@dataclass
class TrashEvent:
    date: str  # YYYY-MM-DD
    type: str  # Restmüll, Altpapier, Biomüll, Gelber Sack
    description: str


class TrashSchedule:
    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.events: List[TrashEvent] = []
        self.config = self._load_config()
        self._load_cache()
    
    def _load_config(self) -> Dict:
        """Load configuration (street, house number, etc.)"""
        if TRASH_CONFIG_FILE.exists():
            with open(TRASH_CONFIG_FILE, "r") as f:
                return json.load(f)
        
        # Default config for user
        default = {
            "street": "Alleestraße",
            "house_number": "58",
            "postal_code": "58097",
            "city": "Hagen",
            "ics_url": None,  # Will be set after fetching
            "last_updated": None,
        }
        self._save_config(default)
        return default
    
    def _save_config(self, config: Dict):
        with open(TRASH_CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    
    def _load_cache(self):
        """Load cached events"""
        if TRASH_CACHE_FILE.exists():
            try:
                with open(TRASH_CACHE_FILE, "r") as f:
                    data = json.load(f)
                    self.events = [TrashEvent(**e) for e in data]
            except Exception:
                self.events = []
    
    def _save_cache(self):
        """Save events to cache"""
        with open(TRASH_CACHE_FILE, "w") as f:
            json.dump([e.__dict__ for e in self.events], f, indent=2)
    
    def parse_ics(self, ics_content: str) -> List[TrashEvent]:
        """Parse ICS calendar content"""
        events = []
        
        # Simple ICS parser
        current_event = {}
        in_event = False
        
        for line in ics_content.split('\n'):
            line = line.strip()
            
            if line == "BEGIN:VEVENT":
                in_event = True
                current_event = {}
            elif line == "END:VEVENT":
                in_event = False
                if current_event.get('date') and current_event.get('summary'):
                    events.append(TrashEvent(
                        date=current_event['date'],
                        type=self._categorize_trash(current_event['summary']),
                        description=current_event['summary'],
                    ))
            elif in_event:
                if line.startswith("DTSTART"):
                    # Parse date: DTSTART;VALUE=DATE:20250115 or DTSTART:20250115
                    match = re.search(r'(\d{8})', line)
                    if match:
                        date_str = match.group(1)
                        current_event['date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                elif line.startswith("SUMMARY"):
                    current_event['summary'] = line.split(':', 1)[-1]
        
        return events
    
    def _categorize_trash(self, summary: str) -> str:
        """Categorize trash type from summary"""
        summary_lower = summary.lower()
        
        if "restmüll" in summary_lower or "rest" in summary_lower:
            return "Restmüll"
        elif "papier" in summary_lower or "altpapier" in summary_lower:
            return "Altpapier"
        elif "bio" in summary_lower:
            return "Biomüll"
        elif "gelb" in summary_lower or "verpackung" in summary_lower:
            return "Gelber Sack"
        elif "sperr" in summary_lower:
            return "Sperrmüll"
        else:
            return "Sonstige"
    
    def fetch_from_ics_url(self, url: str) -> bool:
        """Fetch and parse ICS from URL"""
        try:
            # Create SSL context that doesn't verify (for local testing)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            req = urllib.request.Request(url, headers={
                'User-Agent': 'RyxHub/1.0'
            })
            
            with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
                content = response.read().decode('utf-8')
            
            self.events = self.parse_ics(content)
            self.config['ics_url'] = url
            self.config['last_updated'] = datetime.now().isoformat()
            self._save_config(self.config)
            self._save_cache()
            return True
            
        except Exception as e:
            print(f"Error fetching ICS: {e}")
            return False
    
    def load_from_ics_file(self, file_path: str) -> bool:
        """Load and parse ICS from local file"""
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"ICS file not found: {file_path}")
                return False
            
            content = path.read_text(encoding='utf-8')
            self.events = self.parse_ics(content)
            self.config['ics_file'] = str(path)
            self.config['last_updated'] = datetime.now().isoformat()
            self._save_config(self.config)
            self._save_cache()
            return True
            
        except Exception as e:
            print(f"Error loading ICS file: {e}")
            return False
    
    def get_upcoming(self, days: int = 14) -> List[TrashEvent]:
        """Get upcoming trash collection dates"""
        today = datetime.now().date()
        future = today + timedelta(days=days)
        
        upcoming = []
        for event in self.events:
            try:
                event_date = datetime.strptime(event.date, "%Y-%m-%d").date()
                if today <= event_date <= future:
                    upcoming.append(event)
            except Exception:
                pass
        
        return sorted(upcoming, key=lambda e: e.date)
    
    def get_next(self) -> Optional[TrashEvent]:
        """Get the next trash collection"""
        upcoming = self.get_upcoming(days=30)
        return upcoming[0] if upcoming else None
    
    def get_today(self) -> List[TrashEvent]:
        """Get today's trash collections"""
        today = datetime.now().date().isoformat()
        return [e for e in self.events if e.date == today]
    
    def get_tomorrow(self) -> List[TrashEvent]:
        """Get tomorrow's trash collections"""
        tomorrow = (datetime.now().date() + timedelta(days=1)).isoformat()
        return [e for e in self.events if e.date == tomorrow]
    
    def needs_update(self) -> bool:
        """Check if schedule needs update (> 7 days old)"""
        if not self.config.get('last_updated'):
            return True
        
        try:
            last = datetime.fromisoformat(self.config['last_updated'])
            return (datetime.now() - last).days > 7
        except Exception:
            return True


# Singleton instance
trash_schedule = TrashSchedule()

# Try to load from local ICS file at startup
_ICS_FILE = Path("/home/tobi/Downloads/alleestrassehagen.ics")
if _ICS_FILE.exists() and not trash_schedule.events:
    trash_schedule.load_from_ics_file(str(_ICS_FILE))
