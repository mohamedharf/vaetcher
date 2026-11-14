# Vaetcher: Medical Seminar Voucher & Multi-Party Settlement System

> **Confidentiality Notice:** This project was engineered for a commercial hospitality client ("Vendor X" / a restaurant client) to digitize corporate medical hospitality sponsorships. All client-identifying trademarks, client operational names, and proprietary business identifiers have been sanitized. Certain proprietary source components remain private.

---

## Executive Overview

**Vaetcher** is a dedicated enterprise voucher management and multi-party financial settlement platform built with Python and Django. 

The platform bridges the operational workflows of **hospitality venues (restaurants)**, **pharmaceutical companies**, **medical sales representatives (delegates)**, **partner merchants**, and **physicians (doctors)**. It eliminates manual paper voucher operations, enforces real-time balance integrity at the point of sale (POS), enables flexible partner merchant networks with dynamic markup fees, and provides complete, end-to-end financial settlement lifecycles across all participating parties.

---

## The Business Problem

Pharmaceutical companies regularly contract with hospitality venues (such as our restaurant client) to sponsor scientific medical seminars for physicians. As part of these sponsorship agreements, participating doctors are granted designated dining allowances (vouchers/credits) redeemable at the venue.

Prior to the implementation of Vaetcher, the entire process relied on physical paper vouchers, creating acute operational and financial bottlenecks:
- **Disputed Financial Reconciliations:** Paper coupons were manually collated at month-end, leading to discrepancies between the pharmaceutical sponsors' records and venue billing.
- **Unauthorized Expiration Extensions:** Managing voucher expiration dates manually was prone to human error and disputes over expired tickets.
- **"Lost Voucher" Claims:** Lack of centralized identity tracking made it impossible to verify whether a voucher had been lost, stolen, or already redeemed, leading to duplicate voucher claims and financial leakage.
- **Rigid Redemption Scope:** Doctors were restricted strictly to a single physical location, with no ability to redeem credits across partner venues or split payments.

---

## Core System Architecture & Roles

Vaetcher organizes operational permissions into independent, dedicated dashboards tailored to each stakeholder:

```
+-------------------------------------------------------------------------------+
|                                VENDOR ADMIN                                   |
|                (Full system management, partner setups, settlements)          |
+-------------------+-----------------------+-------------------+---------------+
                    |                       |                   |
                    v                       v                   v
           +-----------------+     +-----------------+  +---------------+
           | PHARMA COMPANY  |     | PARTNER VENDOR  |  |    DOCTOR     |
           | (Sponsorships & |     | (Redemption &   |  | (Self-service |
           |  Settlements)   |     |  Settlements)   |  |  Portal & QR) |
           +--------+--------+     +--------+--------+  +---------------+
                    |                       |
                    v                       v
           +-----------------+     +-----------------+
           |    DELEGATE     |     |  VENDOR CASHIER |
           | (Rep Field Ops) |     | (POS Scan Only) |
           +-----------------+     +-----------------+
```

### 1. Vendor Admin (System & Venue Management)
- Full administrative authority across the entire platform.
- Configures partner merchants (traders) and assigns individual management fee markup percentages.
- Approves seminar event requests and tracks overall system solvency.
- Executes end-to-end **Vendor Settlements**, calculating net merchant dues after deducting administrative management markups.

### 2. Vendor (Restaurant / Partner Merchants)
- Acts as a redemption merchant within the dining network.
- Tracks real-time incoming transactions, gross sales, applied management fees, and net settlement balances.
- Manages dedicated cashier sub-accounts for branch locations.

### 3. Vendor Cashier
- Restricted, point-of-sale operational role.
- Validates doctor credentials at checkout via three real-time verification methods:
  1. Doctor-unique QR code scanning.
  2. Doctor phone number/name directory search.
  3. One-Time Password (OTP) dispatched in real-time to the physician's verified email.
- Executes immediate balance deduction against invoices.

### 4. Pharmaceutical Company
- Independent corporate stakeholder account.
- Allocates seminar budgets using two flexible models:
  - **Per-Doctor Allocation:** Specific allowances assigned to individual attending doctors.
  - **Lump-Sum Event Budget:** Global budget cap for the scientific meeting.
- Tracks voucher distribution, doctor redemption status, and corporate financial settlements.

### 5. Medical Delegate (Sales Representative)
- Field representative assigned to coordinate medical seminars.
- Manages attendee lists and monitors doctor registration.
- Tracks commission rates and reviews dedicated **Delegate Settlements**.

### 6. Doctor (Physician)
- Personalized self-service portal accessible directly by the doctor.
- Displays active vouchers, remaining balances, and expiration timers.
- Generates secure dynamic redemption QR codes.
- **Peer-to-Peer Voucher Transfer:** Allows doctors to transfer a portion of their active credit balance to a peer physician.

---

## Key Technical Features

- **Atomic Real-Time Balance Deduction:** Credits are deducted immediately at the point of purchase rather than recorded as an accrued postpaid tab. Overdrafts and duplicate redemptions are strictly prevented.
- **Multi-Voucher Invoicing (Many-to-Many):** An invoice can split deductions across multiple vouchers held by a doctor in a single transaction.
- **Dynamic Partner Markup System:** The primary venue can expand its network to external dining partners. For transactions occurring at partner venues, the system automatically appends a partner-specific markup percentage (management fee), ensuring transparent commission accounting.
- **Triple-Tier Financial Settlement Engines:**
  - **Vendor Settlement:** Full end-to-end lifecycle reconciling transactions, calculating administrative markups, verifying available balances, and marking payments as complete with uploaded receipts.
  - **Company Settlement:** Reconciles total allocated sponsor budgets against distributed vouchers and consumed physician allowances.
  - **Delegate Settlement:** Calculates performance commissions based on assigned events and registered doctors.
- **Strict Expiration Enforcement:** System-level validation rejects any redemption attempts on expired vouchers.
- **Bilingual & Native RTL Support:** Full native support for Arabic and English with seamless right-to-left (RTL) interface design.

---

## Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | Python / Django |
| **Frontend & Templating** | Django Server-Rendered Templates (No REST framework overhead) |
| **Styling & Layout** | Responsive CSS with complete RTL (Right-to-Left) and LTR bilingual styling |
| **Verification Channels** | QR Code Generation & Verification, SMTP Email Engine for Real-Time OTP delivery |
| **Deployment Model** | Dedicated single-tenant architecture (one instance per client establishment), local environment setup |

---

## Documentation Directory

The `portfolio-docs/` directory contains a complete enterprise technical documentation suite:

1. [System Architecture & Blueprint](SYSTEM_ARCHITECTURE.md) - Three-tier architectural layers, role access boundaries, partner markup routing, and verification topologies.
2. [Operational Workflows & Flowcharts](WORKFLOWS_AND_FLOWCHARTS.md) - Process flowcharts, activity diagrams, and sequence diagrams covering checkout, waterfall deductions, P2P transfers, and settlements.
3. [Entity Relationship Diagram & Data Dictionary](ERD.md) - Comprehensive Mermaid ERD, detailed attribute data dictionary, cardinality analysis, and entity lifecycle state machines.
4. [System Use Cases](USE_CASES.md) - High-level functional use cases categorized by stakeholder role.
5. [Detailed Use Case Specifications](USE_CASE_SPECIFICATIONS.md) - Formal Cockburn-style specifications with main scenarios, extension flows, exceptions, and invariants.
6. [Engineering Case Study](CASE_STUDY.md) - In-depth technical breakdown of balance integrity, multi-voucher settlements, partner markups, and verification flows.
7. [Screenshots Catalog](screenshots/README.md) - Visual guide detailing 18 key application views and dashboard states for manual capture.

