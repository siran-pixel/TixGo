# ShowSpot - Complete Event & Ticket Booking Web Application

**ShowSpot** is a production-grade, full-stack event ticket booking platform inspired by BookMyShow, featuring original modern branding, an interactive dynamic seat map engine, server-enforced 5-minute seat locking, simulated multi-method payment gateway, unique attendee QR code ticket generation, and a dedicated administrative monitoring & data export dashboard.

---

## Key Features

### 1. User & Event Discovery Experience
- **Responsive Landing Page**: Hero banner, search bar with debounce, category quick-scroll filters (Cinema, Theater, Cricket Stadium, Live Concerts, Standup Comedy).
- **Event Overview**: High-resolution event banners, venue metadata, real-time available seat counters, and pricing tier guide.

### 2. Interactive Seating & Real-Time Locking Engine
- **Dynamic Seating Maps by Event Type**:
  - **Cinema / Theater (Max 300 Seats)**: Balcony (₹250) and Standard (₹200) sections with curved screen visual.
  - **Cricket Stadium (10,000 Seats)**: Multi-stand interactive selector (North, South, East, West) with Lower Stand (₹4000) and Upper Stand (₹2000) tiers.
  - **Concert (1,050 Seats)**: Tiered stage view featuring Elite (₹3000), Gold (₹2000), and Silver (₹1000) sections.
  - **General Show**: Configurable numbered seating (strictly enforced &le; ₹1000).
- **Server-Side 5-Minute Seat Lock**:
  - Concurrency-safe atomic database locking preventing double-booking.
  - Real-time countdown timer synchronized with backend expiration.
  - Periodic polling and automatic background cleanup of expired locks.
- **Transaction Limit**: Maximum 10 tickets per booking transaction enforced on client and server.

### 3. Booking Manifest, Payment & QR Tickets
- **Attendee Manifest**: Dynamic collection of Full Name, Age, Phone Number, and City for every individual seat booked.
- **Authoritative Price Breakdown**: Server-side price recalculation (Subtotal + 5% Convenience Fee + 18% GST) preventing frontend price tampering.
- **Simulated Payment Gateway**: Multi-tab interface supporting UPI (QR & VPA), Credit Card, Debit Card, and Net Banking.
- **Consolidated E-Tickets**: Boarding pass-style single-page ticket display showing all attendees with individual unique cryptographic QR codes (`/static/qr/TKT-...png`), print actions, and Web Share API.
- **My Bookings Dashboard**: Manage upcoming and past reservations with instant digital receipt and ticket access.

### 4. Admin Management & Business Analytics
- **Dedicated Admin Authentication**: Completely isolated admin portal at `/admin/login` (`admin1234@gmail.com` / `admin@1234`).
- **Dashboard & KPIs**: Real-time sales volume, revenue velocity, active events, and user counts.
- **Event Management**: Create, edit, and cancel events with automatic procedural seat provisioning.
- **Live Booking Monitor**: Detailed transaction tracking with an interactive modal attendee manifest inspector.
- **Revenue Analytics**: Visual category revenue distribution canvas charts and monthly/daily revenue breakdowns.
- **Data Export Center**: One-click download of booking and financial datasets in **CSV** and **Excel (XLSX)** format via Pandas/OpenPyXL.

---

## Technology Stack

- **Backend**: Python 3.14+ / Flask, Flask-SQLAlchemy, Flask-Mail, Flask-WTF, PyMySQL, Bcrypt / Werkzeug
- **Frontend**: HTML5, CSS3, Vanilla JavaScript (Zero frontend frameworks), Font Awesome 6, Google Fonts
- **Database**: MySQL / SQLite (with automated fallback)
- **Utilities**: `qrcode` & `Pillow` (QR image generation), `pandas` & `openpyxl` (Data exports)
- **Testing**: `pytest`

---

## Project Structure

```
event_ticket_booking/
├── app.py                      # Application factory & seed runner
├── config.py                   # Environment & app configurations
├── requirements.txt            # Pinned dependencies
├── .env.example                # Configuration template
├── .env                        # Local active environment variables
├── README.md                   # Full documentation & setup guide
│
├── database/
│   ├── schema.sql              # MySQL DDL table creation script
│   └── seed.sql                # Sample events & admin seed data
│
├── models/                     # SQLAlchemy Models
│   ├── __init__.py             # Database instance registry
│   ├── user.py                 # Customer accounts & password hashing
│   ├── admin.py                # Admin user accounts
│   ├── otp_verification.py     # 6-digit OTP records & attempt tracking
│   ├── event.py                # Event metadata & pricing calculations
│   ├── seat.py                 # Seat records & section categories
│   ├── seat_lock.py            # 5-minute atomic seat locks
│   ├── booking.py              # Booking transactions & fee breakdown
│   ├── attendee.py             # Attendee details linked to seats
│   ├── payment.py              # Payment gateway records
│   └── ticket.py               # E-Ticket numbers & QR code paths
│
├── routes/                     # Blueprint Route Controllers
│   ├── auth_routes.py          # Signup, Login, OTP & Password Reset
│   ├── event_routes.py         # Landing page & event catalog
│   ├── seat_routes.py          # Dynamic seat maps & locking APIs
│   ├── booking_routes.py       # Attendees, review & user bookings
│   ├── payment_routes.py       # Simulated checkout & atomic confirmation
│   ├── ticket_routes.py        # Consolidated ticket views & downloads
│   └── admin_routes.py         # Admin dashboard, CRUD & data exports
│
├── services/                   # Core Business Logic
│   ├── otp_service.py          # Secure OTP generation & attempt limiter
│   ├── email_service.py        # Email dispatcher with console mock fallback
│   ├── seat_lock_service.py    # 5-min server locking & auto-cleanup
│   ├── seat_generator_service.py# Procedural seating generation
│   ├── booking_service.py      # Transactional booking execution
│   ├── payment_service.py      # Mock payment processor
│   ├── ticket_service.py       # Ticket aggregation service
│   └── export_service.py       # Pandas CSV & OpenPyXL Excel exports
│
├── utils/
│   ├── security.py             # User & Admin session decorators
│   ├── validators.py           # Domain rule & input validation
│   └── qr_generator.py         # High-resolution QR code generator
│
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Global user layout & navbar
│   ├── index.html              # Landing page & event cards
│   ├── login.html              # Customer login
│   ├── signup.html             # Customer signup
│   ├── verify_otp.html         # 6-digit OTP verification & countdown
│   ├── forgot_password.html    # Password recovery request
│   ├── reset_password.html     # New password update
│   ├── event_details.html      # Event overview & pricing guide
│   ├── seat_selection.html     # Dynamic seat map & live lock timer
│   ├── attendee_details.html   # Multi-attendee form collection
│   ├── booking_review.html     # Order review & fee itemization
│   ├── payment.html            # Multi-method payment gateway
│   ├── ticket.html             # Consolidated boarding-pass QR tickets
│   ├── my_bookings.html        # Customer booking history
│   └── admin/                  # Administrative Templates
│       ├── base.html           # Admin shell & sidebar
│       ├── login.html          # Admin login portal
│       ├── dashboard.html      # Metrics & live booking stream
│       ├── events.html         # Event listing & management
│       ├── add_event.html      # Create event & auto-generate seats
│       ├── edit_event.html     # Edit event metadata & status
│       ├── bookings.html       # Bookings monitor & attendee modal
│       ├── users.html          # User directory
│       ├── revenue.html        # Financial analytics & charts
│       └── reports.html        # CSV/Excel export center
│
├── static/
│   ├── css/                    # Modular CSS stylesheets
│   │   ├── style.css           # Design tokens, navbar & footer
│   │   ├── auth.css            # Auth & OTP boxes
│   │   ├── events.css          # Cards & event layouts
│   │   ├── seats.css           # Seat grids & lock summary bar
│   │   ├── booking.css         # Forms & payment multi-tabs
│   │   ├── ticket.css          # Printable boarding-pass styles
│   │   └── admin.css           # Admin metrics, tables & dark UI
│   │
│   ├── js/                     # Vanilla JavaScript Modules
│   │   ├── main.js             # Toasts & navigation toggles
│   │   ├── auth.js             # OTP countdown, input focus & check
│   │   ├── events.js           # Search filter debounce
│   │   ├── seats.js            # Seat engine, locking & polling
│   │   ├── booking.js          # Attendee form handlers
│   │   ├── payment.js          # Payment tab switcher & checkout
│   │   ├── ticket.js           # Web Share API & print
│   │   └── admin.js            # Admin sidebar & UI handlers
│   │
│   └── qr/                     # Generated QR Code image files
│
├── exports/                    # Generated export data files
└── tests/                      # Pytest Automated Test Suite
    ├── conftest.py             # Fixtures & in-memory test database
    ├── test_auth.py            # Registration, OTP & login tests
    ├── test_events.py          # Event catalog & details tests
    ├── test_seats.py           # Locking, limits & concurrency tests
    ├── test_booking.py         # End-to-end booking flow tests
    ├── test_payments.py        # Gateway simulation & pricing tests
    ├── test_admin.py           # Admin authorization & CRUD tests
    └── test_export.py          # CSV & Excel export verification
```

---

## Windows Local Setup & Execution Guide

### Step 1: Clone or Navigate to Project Directory
```powershell
cd r:\project1
```

### Step 2: Create and Activate Python Virtual Environment
```powershell
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```powershell
python -m pip install -r requirements.txt
```

### Step 4: Configure Environment Variables (`.env`)
The repository includes a ready-to-run `.env` file configured for instant development:
```ini
SECRET_KEY=dev-secret-key-showspot-2026-supersecure
DATABASE_URL=sqlite:///event_ticket_booking.db
ADMIN_EMAIL=admin1234@gmail.com
ADMIN_PASSWORD=admin@1234
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=
MAIL_PASSWORD=
MAX_SEATS_PER_BOOKING=10
SEAT_LOCK_DURATION_SECONDS=300
OTP_EXPIRY_SECONDS=300
```

> **Note on MySQL vs SQLite**:
> - To connect to a local MySQL server, update `DATABASE_URL` in `.env`:
>   ```ini
>   DATABASE_URL=mysql+pymysql://root:your_password@localhost:3306/event_ticket_booking
>   ```
> - You can also execute `database/schema.sql` and `database/seed.sql` in MySQL Workbench or the MySQL CLI.
> - When using the default `sqlite:///event_ticket_booking.db`, the database is automatically provisioned and seeded on first launch.

> **Note on Email & OTP Testing**:
> - If live SMTP credentials are empty in `.env`, the system automatically prints OTP verification codes and booking confirmations directly to the terminal console and browser notifications for effortless zero-config testing.

### Step 5: Start the Application
```powershell
python app.py
```

The application will start on `http://127.0.0.1:5000`.

---

## Accessing the Portals

| Portal | URL | Credentials |
| :--- | :--- | :--- |
| **Customer Web Portal** | `http://127.0.0.1:5000` | Sign up with any email (instant login) |
| **Admin Portal** | `http://127.0.0.1:5000/admin/login` | **Email**: `admin1234@gmail.com`<br>**Password**: `admin@1234` |

---

## Running Automated Tests

Execute the comprehensive test suite with `pytest`:
```powershell
python -m pytest tests/ -v
```

This verifies:
1. User registration, password hashing, and OTP verification
2. Landing page, event filters, and catalog JSON APIs
3. 5-minute seat locking, max 10 tickets constraint, and concurrency race conditions
4. End-to-end atomic booking transactions and individual QR code generation
5. Simulated payment gateway and pricing calculation math
6. Admin dashboard authorization, event creation, and procedural seat mapping
7. Pandas / OpenPyXL CSV and Excel data export integrity
#   T i x G o  
 