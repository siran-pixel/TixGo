import json
from datetime import datetime
from typing import List, Dict, Any
from models import db, utcnow


class EventSection(db.Model):
    __tablename__ = "event_sections"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    section_type = db.Column(db.String(50), nullable=False, default="Section")  # 'Section' or 'Stand'
    price = db.Column(db.Numeric(10, 2), nullable=False)
    color = db.Column(db.String(50), nullable=True, default="#6366f1")
    description = db.Column(db.Text, nullable=True)
    row_config = db.Column(db.Text, nullable=True)  # JSON string e.g. [{"row_name": "A", "seat_count": 10}, ...]
    display_order = db.Column(db.Integer, nullable=False, default=1)
    total_seats = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=utcnow)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow)

    def get_row_config(self) -> List[Dict[str, Any]]:
        """Parses the JSON row configuration."""
        if not self.row_config:
            return []
        try:
            return json.loads(self.row_config)
        except (ValueError, TypeError):
            return []

    def set_row_config(self, config: List[Dict[str, Any]]):
        """Sets the JSON row configuration and recalculates total seats."""
        self.row_config = json.dumps(config)
        self.total_seats = sum(int(r.get("seat_count", 0)) for r in config)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "name": self.name,
            "section_type": self.section_type,
            "price": float(self.price),
            "color": self.color or "#6366f1",
            "description": self.description or "",
            "rows": self.get_row_config(),
            "display_order": self.display_order,
            "total_seats": self.total_seats,
        }

    def __repr__(self):
        return f"<EventSection {self.name} (Event {self.event_id}, ₹{self.price})>"
