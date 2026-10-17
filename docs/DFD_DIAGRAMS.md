# TixGo — Data Flow Diagrams (DFD) Level 0 & Level 1

---

## 1. DFD Level 0 — Context Diagram

The **Level 0 Context Diagram** represents the entire **TixGo Ticket Booking Platform** as a single high-level central process (`0.0`), identifying the key external entities that interact with the platform and the primary data flows exchanged between them.

![TixGo DFD Level 0 Context Diagram](C:/Users/siran/.gemini/antigravity/brain/156d7219-eea2-4604-a595-f7a3168241fb/dfd_level_0_1789969300974.jpg)

### 1.1 External Entities
- **Customer / User**: Interacts with the platform to register accounts, explore cricket matches/concerts, select seats, provide attendee details, complete payments, and download QR e-tickets.
- **Admin / Event Manager**: Oversees event lifecycle management, provisions 2,500-seat stadium configurations, audits real-time bookings, and exports financial revenue reports.
- **Payment Gateway / Banking API**: Receives payment authorization requests, validates transactions, and returns payment status confirmations.

### 1.2 Data Flow Summary Table

| Entity | Inbound Data Flow (To System) | Outbound Data Flow (From System) |
| :--- | :--- | :--- |
| **Customer / User** | • Account Registration & Login Credentials<br>• Event Search & Category Filters<br>• Seat Selections & Hold Requests<br>• Attendee Details & Payment Submission | • Profile Access & Session Authentication<br>• Live Event Catalog & 360° Seat Availability<br>• Seat Hold Confirmation & Expiration Timer<br>• Verified QR E-Tickets & Tax Invoices |
| **Admin / Event Manager** | • Event Creation & Pricing Specifications<br>• Stadium Capacity Parameters<br>• Booking Status Inquiries & Cancellation Actions | • Real-Time Occupancy & Sales Dashboard<br>• Booking Ledgers & Attendee Lists<br>• CSV / Excel Financial Audit Exports |
| **Payment Gateway** | • Payment Authorization & Settlement Response<br>• Transaction Reference ID | • Payment Request & Order Amount<br>• Customer Billing Credentials |

### 1.3 Context Architecture (Mermaid Flow)

```mermaid
flowchart TD
    User["👤 Customer / User"]
    Admin["🛡️ Admin / Event Manager"]
    System(("0.0<br/>TixGo Ticket Booking<br/>Platform"))
    PG["💳 Payment Gateway"]

    User -->|"1. Registration, Login & Search"| System
    User -->|"2. Seat Hold & Attendee Info"| System
    System -->|"3. 360° Seat Map & Booking Status"| User
    System -->|"4. Verified QR E-Ticket & Receipt"| User

    Admin -->|"5. Event Creation & Pricing"| System
    Admin -->|"6. Report & Audit Requests"| System
    System -->|"7. Live Analytics & Export Files"| Admin

    System -->|"8. Payment Request & Amount"| PG
    PG -->|"9. Transaction Status & Ref ID"| System
```

---

## 2. DFD Level 1 — Detailed System Decomposition

The **Level 1 Data Flow Diagram** decomposes the central TixGo process into seven core functional sub-processes (`1.0` through `7.0`) and maps data exchanges across five internal data stores (`D1` through `D5`).

![TixGo DFD Level 1 Diagram](C:/Users/siran/.gemini/antigravity/brain/156d7219-eea2-4604-a595-f7a3168241fb/dfd_level_1_1789969332170.jpg)

### 2.1 Core Sub-Processes

1. **Process 1.0 — User Authentication & Profile Management**
   - Validates user sign-up, sign-in, and password reset requests.
   - Reads/writes user credentials to **D1 (Users DB)**.
2. **Process 2.0 — Event Browsing & Search Engine**
   - Handles multi-category filtering (Cricket, Concerts, Comedy) and keyword searches.
   - Reads active events and venue pricing from **D2 (Events & Seats DB)**.
3. **Process 3.0 — 360° Seat Selection & Atomic Locking**
   - Manages interactive 360-degree stadium visualization (10 stands, Lower @ ₹2,000 / Upper @ ₹1,350).
   - Enforces the 10-ticket purchase limit and writes 5-minute atomic holds to **D3 (Seat Locks)**.
4. **Process 4.0 — Attendee Information Management**
   - Collects full names and contact numbers for every individual seat.
   - Prepares booking records and writes to **D4 (Bookings & Attendees DB)**.
5. **Process 5.0 — Payment Processing & Order Finalization**
   - Transmits payment requests to the external Payment Gateway.
   - On successful settlement, updates booking status to Confirmed and writes to **D5 (Payments DB)**.
   - Releases ephemeral seat locks in **D3** and permanently updates seat status to Booked in **D2**.
6. **Process 6.0 — QR E-Ticket & Invoice Generation**
   - Reads confirmed booking data from **D4** and payment tokens from **D5**.
   - Generates cryptographic QR codes and formatted e-ticket boarding passes for download/print.
7. **Process 7.0 — Admin Management & Reporting Engine**
   - Provisions new events and automatically generates 2,500 stadium seat grids in **D2**.
   - Queries **D1**, **D4**, and **D5** to render revenue dashboards and stream CSV/Excel report exports.

### 2.2 Internal Data Stores (Data Store Dictionary)

| Data Store ID | Data Store Name | Description & Key Attributes |
| :--- | :--- | :--- |
| **D1** | **Users DB** | User ID, Full Name, Email, Phone, Salted Password Hash, Account Status, Timestamps. |
| **D2** | **Events & Seats DB** | Event Metadata, 360° Stand Name, Tier (Lower/Upper), Row, Seat Number, Base Price, Status (Available/Booked). |
| **D3** | **Seat Locks** | Lock ID, Seat ID, User/Session ID, Hold Timestamp, Expiration Timestamp (300s window). |
| **D4** | **Bookings & Attendees DB** | Booking Reference, User ID, Event ID, Total Amount, GST Breakdown, Attendee Names, Phone Numbers, QR Token. |
| **D5** | **Payments DB** | Payment ID, Booking ID, Gateway Reference ID, Payment Method, Amount, Status (Success/Refunded). |

### 2.3 Detailed Process Flow Architecture (Mermaid)

```mermaid
flowchart TD
    User["👤 Customer / User"]
    Admin["🛡️ Admin / Event Manager"]
    PG["💳 Payment Gateway"]

    subgraph DataStores ["🗄️ Internal Data Stores"]
        D1[("D1: Users DB")]
        D2[("D2: Events & Seats DB")]
        D3[("D3: Seat Locks")]
        D4[("D4: Bookings & Attendees DB")]
        D5[("D5: Payments DB")]
    end

    subgraph Processes ["⚙️ System Processes"]
        P1(("1.0<br/>User Auth &<br/>Profile"))
        P2(("2.0<br/>Event Catalog<br/>& Search"))
        P3(("3.0<br/>360° Seat Selection<br/>& Atomic Locking"))
        P4(("4.0<br/>Attendee Info<br/>Management"))
        P5(("5.0<br/>Payment<br/>Processing"))
        P6(("6.0<br/>QR Ticket<br/>Generation"))
        P7(("7.0<br/>Admin Management<br/>& Reporting"))
    end

    %% User Auth Flows
    User -->|"Credentials"| P1
    P1 <-->|"Read / Write"| D1
    P1 -->|"Session Auth"| User

    %% Event Catalog Flows
    User -->|"Search & Filter"| P2
    D2 -->|"Active Events"| P2
    P2 -->|"Event Details"| User

    %% Seat Selection Flows
    User -->|"Seat Choices (Max 10)"| P3
    P3 <-->|"Seat Availability"| D2
    P3 -->|"Create 5-Min Hold"| D3
    P3 -->|"Lock Confirmed"| User

    %% Attendee Info Flows
    User -->|"Attendee Details"| P4
    P4 -->|"Store Draft"| D4

    %% Payment Flows
    User -->|"Initiate Checkout"| P5
    P5 <-->|"Authorize Payment"| PG
    P5 -->|"Payment Record"| D5
    P5 -->|"Confirm Booking"| D4
    P5 -->|"Permanent Booked"| D2
    P5 -->|"Clear Locks"| D3

    %% QR Ticket Flows
    D4 -->|"Booking Data"| P6
    D5 -->|"Receipt Data"| P6
    P6 -->|"Verified QR E-Ticket"| User

    %% Admin Flows
    Admin -->|"Create Events & Seats"| P7
    P7 -->|"Auto-Provision 2500 Seats"| D2
    Admin -->|"Generate Reports"| P7
    D4 -->|"Booking Data"| P7
    D5 -->|"Revenue Data"| P7
    P7 -->|"Analytics & CSV/Excel Exports"| Admin
```
