"""
Document AI - Smart Brief/Document Processing
Macht dein Leben einfacher für Briefe und Dokumente
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re
import json

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class DocumentAI:
    """AI-powered document processor for letters and official documents"""
    
    def __init__(self):
        self.templates_dir = Path.home() / ".ryx" / "brief_templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF using pdfplumber"""
        if not PDF_AVAILABLE:
            return "[PDF text extraction not available - install pdfplumber]"
        
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()
        except Exception as e:
            return f"[Error extracting PDF: {e}]"
    
    def analyze_document(self, text: str) -> Dict:
        """Analyze document and extract key information"""
        info = {
            "type": self._detect_document_type(text),
            "sender": self._extract_sender(text),
            "date": self._extract_date(text),
            "subject": self._extract_subject(text),
            "deadlines": self._extract_deadlines(text),
            "requires_response": self._needs_response(text),
            "priority": self._assess_priority(text),
            "summary": self._create_summary(text),
        }
        return info
    
    def _detect_document_type(self, text: str) -> str:
        """Detect type of document"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["rechnung", "invoice", "betrag", "zahlung"]):
            return "Rechnung"
        elif any(word in text_lower for word in ["mahnung", "zahlungserinnerung"]):
            return "Mahnung"
        elif any(word in text_lower for word in ["kündigung", "kündigungsfrist"]):
            return "Kündigung"
        elif any(word in text_lower for word in ["vertrag", "vertragsänderung"]):
            return "Vertrag"
        elif any(word in text_lower for word in ["bescheid", "bewilligung"]):
            return "Behördenbescheid"
        elif any(word in text_lower for word in ["angebot", "kostenvoranschlag"]):
            return "Angebot"
        elif any(word in text_lower for word in ["mahnung", "inkasso"]):
            return "Inkasso"
        elif any(word in text_lower for word in ["versicherung", "schaden"]):
            return "Versicherung"
        else:
            return "Brief"
    
    def _extract_sender(self, text: str) -> Optional[str]:
        """Extract sender from document"""
        lines = text.split("\n")
        # Usually sender is in first few lines
        for i, line in enumerate(lines[:10]):
            if any(keyword in line.lower() for keyword in ["gmbh", "ag", "e.v.", "bank", "kasse", "amt"]):
                return line.strip()
        return None
    
    def _extract_date(self, text: str) -> Optional[str]:
        """Extract date from document"""
        # German date patterns
        date_patterns = [
            r'\d{1,2}\.\d{1,2}\.\d{4}',  # DD.MM.YYYY
            r'\d{1,2}\.\s*\w+\s*\d{4}',   # DD. Month YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            if matches:
                return matches[0]
        return None
    
    def _extract_subject(self, text: str) -> Optional[str]:
        """Extract subject/betreff"""
        # Look for "Betreff:" or similar
        betreff_match = re.search(r'(?:Betreff|Betrifft|Re):\s*(.+)', text, re.IGNORECASE)
        if betreff_match:
            return betreff_match.group(1).strip()
        
        # Otherwise, try to get a meaningful first line
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) > 3:
            return lines[3]  # Usually after header
        return None
    
    def _extract_deadlines(self, text: str) -> List[Dict]:
        """Extract deadlines and response dates"""
        deadlines = []
        text_lower = text.lower()
        
        # Look for deadline keywords
        deadline_keywords = [
            "frist", "bis zum", "spätestens", "deadline", "termin",
            "innerhalb von", "binnen", "vor dem"
        ]
        
        for keyword in deadline_keywords:
            if keyword in text_lower:
                # Find dates near the keyword
                idx = text_lower.index(keyword)
                context = text[max(0, idx-50):min(len(text), idx+100)]
                
                # Extract dates from context
                date_pattern = r'\d{1,2}\.\d{1,2}\.\d{4}'
                dates = re.findall(date_pattern, context)
                
                for date_str in dates:
                    try:
                        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                        days_left = (date_obj - datetime.now()).days
                        
                        deadlines.append({
                            "date": date_str,
                            "context": context[:50],
                            "days_left": days_left,
                            "urgent": days_left < 14
                        })
                    except:
                        pass
        
        return deadlines
    
    def _needs_response(self, text: str) -> bool:
        """Check if document requires a response"""
        text_lower = text.lower()
        
        response_keywords = [
            "bitte antworten", "rückmeldung", "stellungnahme",
            "bitte um", "teilen sie uns mit", "bestätigen sie",
            "antworten sie", "ihre rückmeldung"
        ]
        
        return any(keyword in text_lower for keyword in response_keywords)
    
    def _assess_priority(self, text: str) -> str:
        """Assess document priority"""
        text_lower = text.lower()
        
        high_priority = [
            "dringend", "sofort", "eilig", "mahnung",
            "inkasso", "kündigung", "fristsetzung"
        ]
        
        if any(word in text_lower for word in high_priority):
            return "HOCH"
        
        medium_priority = [
            "rechnung", "frist", "termin", "antwort"
        ]
        
        if any(word in text_lower for word in medium_priority):
            return "MITTEL"
        
        return "NIEDRIG"
    
    def _create_summary(self, text: str) -> str:
        """Create a brief summary"""
        # Take first meaningful paragraph
        paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 50]
        if paragraphs:
            return paragraphs[0][:300] + "..."
        return text[:300] + "..."
    
    def generate_response_template(self, document_info: Dict, response_type: str = "standard") -> str:
        """Generate response letter template"""
        
        templates = {
            "standard": """Betreff: {subject}

Sehr geehrte Damen und Herren,

vielen Dank für Ihr Schreiben vom {date} bezüglich {subject}.

[Ihr Anliegen hier beschreiben]

Mit freundlichen Grüßen
[Ihr Name]""",
            
            "rechnung": """Betreff: Rechnung Nr. {subject}

Sehr geehrte Damen und Herren,

mit diesem Schreiben bestätige ich den Erhalt Ihrer Rechnung vom {date}.

Die Zahlung erfolgt innerhalb der angegebenen Frist.

Mit freundlichen Grüßen
[Ihr Name]""",
            
            "widerspruch": """Betreff: Widerspruch gegen {subject}

Sehr geehrte Damen und Herren,

hiermit lege ich Widerspruch gegen den Bescheid vom {date} ein.

Begründung:
[Ihre Begründung]

Mit freundlichen Grüßen
[Ihr Name]""",
        }
        
        template = templates.get(response_type, templates["standard"])
        
        return template.format(
            subject=document_info.get("subject", "Ihr Schreiben"),
            date=document_info.get("date", datetime.now().strftime("%d.%m.%Y"))
        )
    
    def save_template(self, name: str, content: str):
        """Save custom brief template"""
        template_file = self.templates_dir / f"{name}.txt"
        template_file.write_text(content, encoding="utf-8")
    
    def list_templates(self) -> List[str]:
        """List available templates"""
        return [f.stem for f in self.templates_dir.glob("*.txt")]
    
    def load_template(self, name: str) -> Optional[str]:
        """Load a template"""
        template_file = self.templates_dir / f"{name}.txt"
        if template_file.exists():
            return template_file.read_text(encoding="utf-8")
        return None


# Utility function
def quick_analyze(pdf_path: str) -> Dict:
    """Quick analysis of a PDF document"""
    ai = DocumentAI()
    text = ai.extract_text_from_pdf(Path(pdf_path))
    return ai.analyze_document(text)
