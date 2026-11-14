# System Use Cases

This document outlines the core functional use cases implemented in the **Vaetcher** platform, categorized by stakeholder role. Each use case reflects production-validated workflows governing voucher issuance, multi-party redemptions, and financial reconciliations.

---

## 1. Vendor Admin (System & Venue Management)

The Vendor Admin holds primary administrative control over the platform, overseeing partner networks, seminar approvals, and overall financial health.

### UC-VA01: Partner Merchant Onboarding & Dynamic Markup Configuration
- **Primary Actor:** Vendor Admin
- **Preconditions:** Authenticated as Vendor Admin.
- **Workflow:**
  1. Admin registers a new partner merchant (Trader) into the dining network.
  2. Admin defines the merchant profile (category, contact info, banking and electronic wallet details).
  3. Admin configures the **Management Fee Percentage** (markup %) specific to that merchant.
  4. System establishes the merchant profile, enabling the venue to process vouchers with the designated commission rate.
- **Business Rule:** If a voucher is redeemed at an external partner merchant instead of the primary venue, the configured markup percentage is automatically computed on each transaction invoice and credited to the venue during settlement.

### UC-VA02: Event / Seminar Approval & Voucher Issuance
- **Primary Actor:** Vendor Admin
- **Preconditions:** Pharmaceutical company or delegate submits a seminar request.
- **Workflow:**
  1. Admin reviews seminar details, including dates, corporate sponsor, assigned delegates, and invited doctors.
  2. Admin confirms voucher configuration: individual voucher face value and expiration duration (in days).
  3. Upon approval, the system transitions the event to an active state and generates digital vouchers for all designated physicians with strict expiration dates.
- **Business Rule:** Vouchers are generated with an active status and an initial balance equal to the approved face value. Expiration dates are strictly computed from the event configuration.

### UC-VA03: End-to-End Vendor Settlement Execution
- **Primary Actor:** Vendor Admin
- **Preconditions:** Partner merchant has accumulated completed redemption transactions.
- **Workflow:**
  1. Admin initiates a Vendor Settlement for a selected partner merchant.
  2. System aggregates all eligible transactions associated with the partner and its cashier sub-accounts.
  3. System calculates:
     - **Gross Amount Spent:** Total dining value consumed at the partner merchant.
     - **Administrative Commission:** Total management markup fees retained by the primary venue.
     - **Net Payout:** Verified net amount payable to the partner merchant.
  4. System validates available solvency: settlement amount cannot exceed accumulated unsettled balance.
  5. Admin records the payment method (Bank Transfer, Cash, Check), attaches payment receipt imagery, and marks the settlement as Completed.
- **Business Rule:** Linked transactions are flagged as settled, preventing duplicate claims or overlapping settlement requests.

---

## 2. Vendor (Restaurant / Partner Merchant)

Represents an authorized merchant venue where doctors can redeem their vouchers.

### UC-VM01: Merchant Performance & Sales Monitoring
- **Primary Actor:** Partner Merchant Admin
- **Preconditions:** Authenticated as Vendor.
- **Workflow:**
  1. Merchant logs into the dedicated merchant dashboard.
  2. System displays real-time key metrics: total voucher sales volume, count of transactions processed, deducted administrative markups, and outstanding uncollected balance.
  3. Merchant inspects itemized transaction histories, including customer doctor details, invoice identifiers, and timestamps.

### UC-VM02: Cashier Sub-Account Provisioning
- **Primary Actor:** Partner Merchant Admin
- **Preconditions:** Authenticated as Vendor.
- **Workflow:**
  1. Merchant creates dedicated cashier operator credentials for branch service staff.
  2. System links cashier accounts directly to the parent vendor hierarchy (`parent_vendor`).
  3. Cashier permissions are restricted strictly to POS verification and transaction processing, shielding administrative financial ledgers from operational personnel.

---

## 3. Vendor Cashier (Point of Sale Checkout)

Operational role focused entirely on rapid, secure customer verification and balance redemption at the POS terminal.

### UC-VC01: Doctor Identity Verification via QR Code
- **Primary Actor:** Vendor Cashier
- **Preconditions:** Physician presents their personal digital pass.
- **Workflow:**
  1. Cashier opens the POS scanning interface.
  2. Cashier scans the physician's unique QR code.
  3. System resolves the doctor profile, verifies account activity, and loads available active vouchers and aggregate balance in real time.

### UC-VC02: Doctor Identity Verification via Directory Lookup
- **Primary Actor:** Vendor Cashier
- **Preconditions:** Physician does not have an active device or QR code available.
- **Workflow:**
  1. Cashier queries the verified doctor directory using the physician's registered phone number or full name.
  2. System returns matching verified records.
  3. Cashier selects the confirmed physician and inspects active balance limits.

### UC-VC03: High-Security Verification via Email OTP
- **Primary Actor:** Vendor Cashier & Physician
- **Preconditions:** Additional transaction verification required.
- **Workflow:**
  1. Cashier triggers an OTP dispatch from the checkout interface.
  2. System generates a time-bound One-Time Password and sends it immediately via SMTP email to the physician's registered address.
  3. Physician retrieves the code and provides it to the cashier.
  4. Cashier inputs the OTP into the system for verification before invoice processing is unlocked.

### UC-VC04: Immediate Transaction Processing & Multi-Voucher Deduction
- **Primary Actor:** Vendor Cashier
- **Preconditions:** Doctor verified; positive voucher balance exists.
- **Workflow:**
  1. Cashier inputs the physical invoice number, billing amount, and items description.
  2. System checks the doctor's active vouchers, automatically filtering out expired or exhausted vouchers.
  3. If the invoice amount requires multiple vouchers, the system applies a Many-to-Many deduction model, exhausting older vouchers first and splitting residual amounts across subsequent vouchers.
  4. If operating at an external partner merchant, the system calculates and logs the configured administrative markup fee.
  5. The balance is immediately and atomically deducted from the database. The system outputs a confirmed transaction receipt.
- **Business Rule:** Balances are deducted instantly. Transactions cannot exceed the cumulative active, unexpired balance held by the doctor.

---

## 4. Pharmaceutical Company

Corporate sponsor managing educational event sponsorship and tracking return on hospitality investment.

### UC-PC01: Medical Seminar Request & Budget Allocation
- **Primary Actor:** Pharmaceutical Company Representative
- **Preconditions:** Authenticated as Company user.
- **Workflow:**
  1. Company initiates an Event Request from the corporate dashboard.
  2. Company selects the budget allocation model:
     - **Model A (Individual Doctor Allocation):** Specifies a roster of physicians with designated voucher limits per doctor.
     - **Model B (Lump-Sum Event Budget):** Specifies a global seminar budget cap distributed among participating attendees.
  3. Company assigns responsible medical sales representatives (Delegates) to supervise the event.
  4. Request is submitted for Venue Admin approval.

### UC-PC02: Corporate Financial Settlement & Surplus Reconciliation
- **Primary Actor:** Pharmaceutical Company Representative & Venue Admin
- **Preconditions:** Sponsored event has concluded or reached reconciliation period.
- **Workflow:**
  1. Corporate user reviews the Company Settlement view.
  2. System computes:
     - **Total Budget Allocated:** Total agreed funding cap.
     - **Total Vouchers Distributed:** Cumulative face value of issued credits.
     - **Actual Dining Spend:** Real amount consumed by doctors at the venue.
     - **Unconsumed Surplus:** Remaining unspent balance.
  3. Parties reconcile final amounts due, attach settlement documentation/receipts, and close the corporate billing ledger (Pending $\rightarrow$ Partial $\rightarrow$ Completed).

---

## 5. Medical Delegate (Sales Representative)

Field operator facilitating doctor engagement and seminar coordination.

### UC-MD01: Field Event & Physician Roster Management
- **Primary Actor:** Medical Delegate
- **Preconditions:** Authenticated as Delegate.
- **Workflow:**
  1. Delegate accesses assigned medical seminars.
  2. Delegate registers new doctor profiles or links existing doctors from the system registry.
  3. Delegate monitors physician voucher claim status and attendance readiness.

### UC-MD02: Commission Tracking & Delegate Settlement
- **Primary Actor:** Medical Delegate
- **Preconditions:** Assigned events completed.
- **Workflow:**
  1. Delegate reviews the Delegate Settlement dashboard.
  2. System calculates performance metrics: total assigned events, registered doctor headcount, agreed commission percentage, and total calculated commission payout.
  3. Delegate tracks payout verification and settlement status directly with corporate management.

---

## 6. Doctor (Physician Attendee)

Beneficiary of corporate medical sponsorship enjoying frictionless dining credits.

### UC-DR01: Self-Service Balance & Voucher Inquiries
- **Primary Actor:** Doctor
- **Preconditions:** Authenticated as Doctor.
- **Workflow:**
  1. Doctor logs into the mobile-responsive portal.
  2. System presents individual voucher balances, sponsoring event names, issue dates, and days remaining until expiration.
  3. Doctor accesses their personal QR code pass ready for POS presentation.

### UC-DR02: Peer-to-Peer Voucher Balance Transfer
- **Primary Actor:** Doctor (Sender) & Colleague Doctor (Recipient)
- **Preconditions:** Sender holds an active, unexpired voucher with an available balance.
- **Workflow:**
  1. Doctor selects an active voucher and chooses the "Transfer Balance" action.
  2. Doctor searches and designates a colleague physician registered on the platform.
  3. Doctor enters the transfer amount.
  4. System validates:
     - Transfer amount does not exceed current voucher balance.
     - Voucher is not expired or inactive.
     - Recipient doctor profile is valid and active.
  5. System executes the transfer: deducts balance from the sender's voucher, credits the recipient's voucher ledger, and creates an immutable **Voucher Transfer** audit log.
- **Business Rule:** Transfers are instantaneous and irrevocable once confirmed.
