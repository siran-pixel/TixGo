import json
import re
from typing import List, Dict, Any, Tuple, Optional
from models import db, Seat, Event, EventSection, SeatLock


def get_default_sections_for_event_type(event_type: str) -> List[Dict[str, Any]]:
    """Returns sensible default dynamic section/row configurations by event category."""
    norm_type = (event_type or "").capitalize()

    if norm_type == "Concert":
        return [
            {
                "name": "Elite",
                "section_type": "Section",
                "price": 2500.0,
                "color": "#a855f7",
                "description": "Front stage VIP experience with plush seating",
                "rows": [
                    {"row_name": "A", "seat_count": 10},
                    {"row_name": "B", "seat_count": 10},
                    {"row_name": "C", "seat_count": 10},
                ],
            },
            {
                "name": "Platinum",
                "section_type": "Section",
                "price": 1500.0,
                "color": "#3b82f6",
                "description": "Prime elevated view directly facing the main stage",
                "rows": [
                    {"row_name": "A", "seat_count": 10},
                    {"row_name": "B", "seat_count": 15},
                    {"row_name": "C", "seat_count": 15},
                    {"row_name": "D", "seat_count": 20},
                ],
            },
            {
                "name": "Silver",
                "section_type": "Section",
                "price": 800.0,
                "color": "#94a3b8",
                "description": "Great atmosphere with clear acoustics",
                "rows": [
                    {"row_name": "A", "seat_count": 20},
                    {"row_name": "B", "seat_count": 20},
                    {"row_name": "C", "seat_count": 20},
                    {"row_name": "D", "seat_count": 25},
                    {"row_name": "E", "seat_count": 25},
                ],
            },
        ]
    elif norm_type == "Cricket":
        return [
            {
                "name": "North Stand",
                "section_type": "Stand",
                "price": 500.0,
                "color": "#2563eb",
                "description": "Direct view of batsman crease and sightscreen",
                "rows": [
                    {"row_name": "A", "seat_count": 50},
                    {"row_name": "B", "seat_count": 50},
                    {"row_name": "C", "seat_count": 60},
                ],
            },
            {
                "name": "South Stand",
                "section_type": "Stand",
                "price": 750.0,
                "color": "#0ea5e9",
                "description": "Pavilion end view with energetic supporters block",
                "rows": [
                    {"row_name": "A", "seat_count": 40},
                    {"row_name": "B", "seat_count": 50},
                    {"row_name": "C", "seat_count": 50},
                ],
            },
            {
                "name": "VIP Stand",
                "section_type": "Stand",
                "price": 2000.0,
                "color": "#eab308",
                "description": "Premium hospitality pavilion with complimentary refreshments",
                "rows": [
                    {"row_name": "A", "seat_count": 20},
                    {"row_name": "B", "seat_count": 20},
                ],
            },
        ]
    else:
        # General / Theater / Comedy Show
        return [
            {
                "name": "VIP Front",
                "section_type": "Section",
                "price": 999.0,
                "color": "#f97316",
                "description": "Front row seats near the stage",
                "rows": [
                    {"row_name": "A", "seat_count": 15},
                    {"row_name": "B", "seat_count": 15},
                ],
            },
            {
                "name": "General Admission",
                "section_type": "Section",
                "price": 499.0,
                "color": "#64748b",
                "description": "Standard comfortable tiered seating",
                "rows": [
                    {"row_name": "C", "seat_count": 20},
                    {"row_name": "D", "seat_count": 20},
                    {"row_name": "E", "seat_count": 20},
                ],
            },
        ]


def _clean_prefix(name: str) -> str:
    """Creates a short, clean alphanumeric uppercase code for a section/stand."""
    clean = re.sub(r"[^A-Za-z0-9]", "", name).upper()
    return clean[:6] if len(clean) >= 3 else (clean + "SEC")[:6]


def provision_dynamic_layout(
    event: Event,
    sections_config: List[Dict[str, Any]],
    preserve_booked: bool = False
) -> Tuple[bool, str, int]:
    """
    Provisions dynamic sections, rows, and seats for an event based on admin configuration.

    Validation & Safety:
    - Verifies that no booked seats are destroyed.
    - Ensures unique seat identifiers across all sections.
    - Enforces positive prices and valid seat counts.
    - Atomic database commit with rollback on error.
    """
    if not sections_config:
        return False, "At least one section or stand is required.", 0

    # Check for existing bookings
    booked_count = Seat.query.filter_by(event_id=event.id, status="BOOKED").count()
    if booked_count > 0 and not preserve_booked:
        return False, f"Cannot overwrite seat layout: this event already has {booked_count} booked ticket(s). Modifications are locked to preserve customer bookings.", 0

    try:
        # Clear temporary seat locks
        SeatLock.query.filter(
            SeatLock.seat_id.in_(
                db.session.query(Seat.id).filter_by(event_id=event.id)
            )
        ).delete(synchronize_session=False)

        # Remove existing unbooked seats and sections
        if booked_count == 0:
            Seat.query.filter_by(event_id=event.id).delete(synchronize_session=False)
            EventSection.query.filter_by(event_id=event.id).delete(synchronize_session=False)
            db.session.flush()

        created_sections: List[EventSection] = []
        seats_to_insert: List[Seat] = []
        generated_seat_identifiers = set()

        # Count total sections to decide whether prefixing is needed for row uniqueness
        total_sections = len(sections_config)
        all_row_names = []
        for sec_data in sections_config:
            for r in sec_data.get("rows", []):
                all_row_names.append(str(r.get("row_name", "")).strip().upper())
        has_duplicate_rows = len(all_row_names) != len(set(all_row_names))

        for sec_idx, sec_data in enumerate(sections_config):
            sec_name = str(sec_data.get("name", "")).strip()
            if not sec_name:
                sec_name = f"Section {sec_idx + 1}"

            sec_type = str(sec_data.get("section_type", "Section")).strip()
            if not sec_type:
                sec_type = "Stand" if event.event_type.capitalize() == "Cricket" else "Section"

            try:
                price = round(float(sec_data.get("price", 500.0)), 2)
                if price <= 0:
                    return False, f"Price for section '{sec_name}' must be greater than ₹0.", 0
            except (ValueError, TypeError):
                return False, f"Invalid price value for section '{sec_name}'.", 0

            color = str(sec_data.get("color", "#6366f1")).strip() or "#6366f1"
            description = str(sec_data.get("description", "")).strip()

            raw_rows = sec_data.get("rows", [])
            if not raw_rows:
                return False, f"Section '{sec_name}' must have at least one row configured.", 0

            cleaned_rows: List[Dict[str, Any]] = []
            sec_total_seats = 0

            for r_idx, r_data in enumerate(raw_rows):
                r_name = str(r_data.get("row_name", "")).strip()
                if not r_name:
                    r_name = chr(65 + r_idx) if r_idx < 26 else f"R{r_idx + 1}"

                try:
                    s_count = int(r_data.get("seat_count", 0))
                    if s_count <= 0 or s_count > 500:
                        return False, f"Row '{r_name}' in section '{sec_name}' must have between 1 and 500 seats.", 0
                except (ValueError, TypeError):
                    return False, f"Invalid seat count in row '{r_name}' of section '{sec_name}'.", 0

                cleaned_rows.append({"row_name": r_name, "seat_count": s_count})
                sec_total_seats += s_count

            event_sec = EventSection(
                event_id=event.id,
                name=sec_name,
                section_type=sec_type,
                price=price,
                color=color,
                description=description,
                row_config=json.dumps(cleaned_rows),
                display_order=sec_idx + 1,
                total_seats=sec_total_seats,
            )
            db.session.add(event_sec)
            db.session.flush()  # Generates event_sec.id
            created_sections.append(event_sec)

            # Generate individual seats for each row
            sec_code = _clean_prefix(sec_name)
            for row in cleaned_rows:
                r_name = row["row_name"]
                seat_count = row["seat_count"]

                for s_num in range(1, seat_count + 1):
                    # Guarantee unique seat number within the event
                    if total_sections > 1 or has_duplicate_rows:
                        seat_number = f"{sec_code}-{r_name}{s_num}"
                    else:
                        seat_number = f"{r_name}{s_num}"

                    # If duplicate collision occurs, make sure it's unique
                    if seat_number in generated_seat_identifiers:
                        seat_number = f"{sec_code}-{r_name}-{s_num:02d}"

                    generated_seat_identifiers.add(seat_number)

                    seats_to_insert.append(
                        Seat(
                            event_id=event.id,
                            seat_number=seat_number,
                            section=sec_name,
                            category=sec_name,
                            price=price,
                            status="AVAILABLE",
                            section_id=event_sec.id,
                            row_label=r_name,
                            seat_index=s_num,
                        )
                    )

        # Bulk insert seats
        db.session.bulk_save_objects(seats_to_insert)
        event.total_seats = len(seats_to_insert)
        db.session.commit()

        return True, f"Successfully provisioned dynamic layout: {len(seats_to_insert)} seats across {len(created_sections)} sections/stands.", len(seats_to_insert)

    except Exception as e:
        db.session.rollback()
        return False, f"Database error generating seat layout: {str(e)}", 0


def generate_seats_for_event(
    event: Event,
    custom_price: float = 500.0,
    custom_capacity: int = 200
) -> int:
    """
    Standard / Default provisioning service maintaining full backwards-compatibility.
    Also creates EventSection metadata records so all events enjoy unified dynamic layout support.
    """
    event_type = event.event_type.capitalize()
    seats_to_insert: List[Seat] = []

    # Clear any previous sections for this event
    EventSection.query.filter_by(event_id=event.id).delete(synchronize_session=False)
    db.session.flush()

    if event_type == "Cricket":
        # 360° Circular Stadium Layout (10 Stands)
        stadium_stands = [
            ("A", "Stand A"),
            ("B", "Stand B"),
            ("C", "Stand C"),
            ("D", "Stand D"),
            ("E", "Stand E"),
            ("F", "Stand F"),
            ("G", "Stand G"),
            ("H", "Stand H"),
            ("I", "Stand I"),
            ("PAV", "Pavilion End"),
        ]

        order = 1
        for code, name in stadium_stands:
            # Lower Stand section
            lower_rows = [{"row_name": f"L{r}", "seat_count": 25} for r in range(1, 7)]
            sec_lower = EventSection(
                event_id=event.id,
                name=f"{name} - Lower",
                section_type="Stand",
                price=2000.00,
                color="#2563eb",
                description=f"{name} Lower Tier (Rows L1-L6, 25 seats/row)",
                row_config=json.dumps(lower_rows),
                display_order=order,
                total_seats=150,
            )
            db.session.add(sec_lower)
            db.session.flush()
            order += 1

            for r in range(1, 7):
                for s in range(1, 26):
                    seats_to_insert.append(Seat(
                        event_id=event.id,
                        seat_number=f"{code}-L{r}-{s:02d}",
                        section=f"{name} - Lower",
                        category="Lower Stand",
                        price=2000.00,
                        status="AVAILABLE",
                        section_id=sec_lower.id,
                        row_label=f"L{r}",
                        seat_index=s,
                    ))

            # Upper Stand section
            upper_rows = [{"row_name": f"U{r}", "seat_count": 20} for r in range(1, 6)]
            sec_upper = EventSection(
                event_id=event.id,
                name=f"{name} - Upper",
                section_type="Stand",
                price=1350.00,
                color="#0ea5e9",
                description=f"{name} Upper Tier (Rows U1-U5, 20 seats/row)",
                row_config=json.dumps(upper_rows),
                display_order=order,
                total_seats=100,
            )
            db.session.add(sec_upper)
            db.session.flush()
            order += 1

            for r in range(1, 6):
                for s in range(1, 21):
                    seats_to_insert.append(Seat(
                        event_id=event.id,
                        seat_number=f"{code}-U{r}-{s:02d}",
                        section=f"{name} - Upper",
                        category="Upper Stand",
                        price=1350.00,
                        status="AVAILABLE",
                        section_id=sec_upper.id,
                        row_label=f"U{r}",
                        seat_index=s,
                    ))

    elif event_type == "Concert":
        # 1050 seats: Elite (50 @ 3000), Gold (200 @ 2000), Silver (800 @ 1000)
        # Elite Section
        elite_rows = [{"row_name": "E", "seat_count": 50}]
        sec_elite = EventSection(
            event_id=event.id,
            name="Elite Section",
            section_type="Section",
            price=3000.00,
            color="#a855f7",
            description="Front row stage-side luxury seating",
            row_config=json.dumps(elite_rows),
            display_order=1,
            total_seats=50,
        )
        db.session.add(sec_elite)
        db.session.flush()

        for i in range(1, 51):
            seats_to_insert.append(Seat(
                event_id=event.id,
                seat_number=f"ELITE-{i}",
                section="Elite Section",
                category="Elite",
                price=3000.00,
                status="AVAILABLE",
                section_id=sec_elite.id,
                row_label="E",
                seat_index=i,
            ))

        # Gold Section
        gold_rows = [{"row_name": f"G{r}", "seat_count": 20} for r in range(1, 11)]
        sec_gold = EventSection(
            event_id=event.id,
            name="Gold Section",
            section_type="Section",
            price=2000.00,
            color="#eab308",
            description="Premium central seating block",
            row_config=json.dumps(gold_rows),
            display_order=2,
            total_seats=200,
        )
        db.session.add(sec_gold)
        db.session.flush()

        for r in range(1, 11):
            for s in range(1, 21):
                seats_to_insert.append(Seat(
                    event_id=event.id,
                    seat_number=f"G{r}-{s}",
                    section="Gold Section",
                    category="Gold",
                    price=2000.00,
                    status="AVAILABLE",
                    section_id=sec_gold.id,
                    row_label=f"G{r}",
                    seat_index=s,
                ))

        # Silver Section
        silver_rows = [{"row_name": f"S{r}", "seat_count": 40} for r in range(1, 21)]
        sec_silver = EventSection(
            event_id=event.id,
            name="Silver Section",
            section_type="Section",
            price=1000.00,
            color="#94a3b8",
            description="Tiered auditorium seating",
            row_config=json.dumps(silver_rows),
            display_order=3,
            total_seats=800,
        )
        db.session.add(sec_silver)
        db.session.flush()

        for r in range(1, 21):
            for s in range(1, 41):
                seats_to_insert.append(Seat(
                    event_id=event.id,
                    seat_number=f"S{r}-{s}",
                    section="Silver Section",
                    category="Silver",
                    price=1000.00,
                    status="AVAILABLE",
                    section_id=sec_silver.id,
                    row_label=f"S{r}",
                    seat_index=s,
                ))

    else:
        # General Show: custom capacity and price <= 1000
        price = min(float(custom_price), 1000.00)
        cap = max(10, min(custom_capacity, 1000))
        seats_per_row = 20
        total_rows = (cap + seats_per_row - 1) // seats_per_row

        gen_rows = []
        for r_idx in range(total_rows):
            row_letter = chr(65 + r_idx) if r_idx < 26 else f"R{r_idx + 1}"
            seats_in_this_row = min(seats_per_row, cap - (r_idx * seats_per_row))
            gen_rows.append({"row_name": row_letter, "seat_count": seats_in_this_row})

        sec_gen = EventSection(
            event_id=event.id,
            name="General Hall",
            section_type="Section",
            price=price,
            color="#06b6d4",
            description="General admission hall seating",
            row_config=json.dumps(gen_rows),
            display_order=1,
            total_seats=cap,
        )
        db.session.add(sec_gen)
        db.session.flush()

        count = 0
        for r_idx in range(total_rows):
            row_letter = chr(65 + r_idx) if r_idx < 26 else f"R{r_idx + 1}"
            for s in range(1, seats_per_row + 1):
                count += 1
                if count > cap:
                    break
                seats_to_insert.append(Seat(
                    event_id=event.id,
                    seat_number=f"{row_letter}{s}",
                    section="General Hall",
                    category="General",
                    price=price,
                    status="AVAILABLE",
                    section_id=sec_gen.id,
                    row_label=row_letter,
                    seat_index=s,
                ))

    # Bulk insert for optimal performance
    db.session.bulk_save_objects(seats_to_insert)
    event.total_seats = len(seats_to_insert)
    db.session.commit()

    return len(seats_to_insert)
