# Detailed Use Case Specifications

This document provides formal, exhaustive **Use Case Specifications** for the core business interactions across the **Vaetcher** platform. 

Each specification follows the industry-standard template (Actor, Preconditions, Main Success Scenario, Alternative & Exception Flows, Postconditions, and Business Invariants), establishing a comprehensive functional audit of the software.

---

## Index of Use Case Specifications

| ID | Title | Primary Actor | Domain Scope |
| :--- | :--- | :--- | :--- |
| **UC-SPEC-01** | Partner Merchant Onboarding & Dynamic Markup Setup | Vendor Admin | Merchant Network Management |
| **UC-SPEC-02** | Medical Seminar Request & Budget Allocation | Pharma Company / Delegate | Event Sponsorship |
| **UC-SPEC-03** | Seminar Approval & Digital Voucher Generation | Vendor Admin | Voucher Lifecycle |
| **UC-SPEC-04** | POS Tri-Factor Identity Verification | Vendor Cashier | Identity & Authentication |
| **UC-SPEC-05** | Real-Time Atomic Multi-Voucher Checkout | Vendor Cashier | Transaction Processing |
| **UC-SPEC-06** | Peer-to-Peer Voucher Balance Transfer | Doctor | Balance Management |
| **UC-SPEC-07** | End-to-End Vendor Settlement Execution | Vendor Admin | Financial Settlements |
| **UC-SPEC-08** | Corporate Sponsor Budget Reconciliation | Pharma Company / Admin | Corporate Financial Audit |
| **UC-SPEC-09** | Delegate Commission Review & Settlement | Medical Delegate / Admin | Representative Compensation |

---

## UC-SPEC-01: Partner Merchant Onboarding & Dynamic Markup Setup

### Summary
The Venue Administrator configures an external dining merchant (Trader) into the digital voucher redemption network, specifying contact metadata, financial disbursement destinations, and a custom administrative management markup percentage.

- **Primary Actor:** Vendor Admin
- **Secondary Actors:** Partner Merchant Operations Team
- **Preconditions:** Vendor Admin is authenticated with root administrative privileges.
- **Trigger:** Primary venue executes a partnership contract with an external dining establishment.

### Main Success Scenario
1. Admin navigates to the Partner Merchant Management module.
2. Admin clicks "Register Partner Merchant" and inputs the merchant profile details:
   - Business trading name, physical address, and category (e.g., Restaurant, Cafe).
   - Operations contact person, business email, and direct telephone.
   - Commercial banking settlement details and electronic wallet identifiers.
3. Admin sets the **Management Fee Percentage** ($Markup\%$) applicable to this merchant (e.g., $25.00\%$).
4. Admin toggles **Has Management Fee** to `True` and sets merchant status to `Active`.
5. Admin submits the form.
6. System verifies uniqueness of merchant name and contact records.
7. System persists the new merchant profile into the database.
8. System displays confirmation and generates a parent vendor identifier for cashier provisioning.

### Extensions & Alternative Flows
- **3a. Merchant Exempt from Administrative Markup:**
  - If the partnership agreement is non-commissionable (e.g., subsidiary branch), Admin toggles **Has Management Fee** to `False`.
  - System disables markup calculation for transactions occurring at this venue ($Markup\% = 0.00\%$).
- **6a. Duplicate Merchant Registration Conflict:**
  - System detects existing registered merchant with the same trading name or phone.
  - System halts submission, displays validation alert, and prompts Admin to resolve conflict.

### Postconditions
- **Success Guarantee:** The merchant is active in the network; cashiers can be provisioned under its hierarchy; transactions routed through this merchant automatically append the configured markup.
- **Failure Guarantee:** Database rolls back cleanly; no partial or duplicate merchant records are created.

---

## UC-SPEC-02: Medical Seminar Request & Budget Allocation

### Summary
A pharmaceutical company or authorized medical delegate submits a medical seminar sponsorship request, defining attendee physician rosters and selecting an allocation model.

- **Primary Actor:** Pharmaceutical Company Representative / Medical Delegate
- **Secondary Actors:** Venue Administrator
- **Preconditions:** Sponsoring user is authenticated with corporate permissions.
- **Trigger:** Sponsoring pharmaceutical company finalizes scientific symposium planning.

### Main Success Scenario
1. Sponsoring user accesses the Event Request module.
2. User inputs seminar details: title, proposed calendar date, and medical specialty.
3. User designates the responsible Medical Delegate(s) assigned to manage field operations.
4. User selects the **Financial Allocation Model**:
   - **Model A (Individual Doctor Allowance):** User specifies attending physicians and assigns an individual voucher limit to each doctor.
   - **Model B (Lump-Sum Event Budget):** User defines a global aggregate budget ceiling for the symposium.
5. User specifies desired voucher validity window (e.g., 90 days from seminar date).
6. User reviews and submits the seminar request.
7. System creates an `EventRequest` record with status `PENDING`.
8. System alerts Venue Administration that a new symposium awaits authorization.

### Extensions & Alternative Flows
- **4a. New Doctor Not Yet in System Database:**
  - Sponsor inputs details for a physician not currently registered.
  - System logs an `EventRequestDoctor` placeholder record with provided name, phone, and specialty.
  - Upon event approval, system provisions new physician credentials automatically.
- **6a. Validation Error - Total Allocations Exceed Budget Ceiling:**
  - In Model A, if the cumulative sum of individual doctor vouchers exceeds the contracted maximum budget, system blocks submission and highlights the budget variance.

### Postconditions
- **Success Guarantee:** Seminar request is securely stored in `PENDING` state with complete attendee rosters and budget definitions.
- **Failure Guarantee:** No uncommitted records or partial doctor allocations persist in the database.

---

## UC-SPEC-03: Seminar Approval & Digital Voucher Generation

### Summary
The Venue Administrator reviews, approves, and activates a pending seminar sponsorship, triggering automated bulk generation of digital vouchers with strict chronological expiration dates.

- **Primary Actor:** Vendor Admin
- **Secondary Actors:** Pharmaceutical Sponsor, Attending Physicians
- **Preconditions:** Event request exists in `PENDING` status.
- **Trigger:** Venue administration confirms payment terms (Cash or Deferred Credit) with corporate sponsor.

### Main Success Scenario
1. Admin opens the Event Approvals dashboard and inspects the pending seminar request.
2. Admin validates corporate sponsor credit standing and confirms event payment terms (`CASH` or `DEFERRED`).
3. Admin confirms individual voucher face value and expiration duration (in days).
4. Admin clicks "Authorize Seminar & Issue Vouchers".
5. System initiates an atomic database transaction:
   - Transitions event status to `APPROVED`.
   - Provisions accounts for any new attending physicians.
   - Calculates hard expiration date: $ExpiryDate = CurrentDate + VoucherExpiryDays$.
   - Generates digital `Voucher` records for all rostered physicians with `initial_value` and `current_balance` set to the authorized allowance.
   - Sets each voucher's `is_active` status to `True`.
6. Atomic transaction commits.
7. System updates physician mobile dashboards; digital passes reflect the newly credited allowances.
8. System logs confirmation and archives event request.

### Extensions & Alternative Flows
- **2a. Administrative Rejection:**
  - Admin rejects request due to scheduling conflicts or sponsor credit issues.
  - Admin records rejection justification.
  - System transitions event status to `REJECTED`; no vouchers are created.

### Postconditions
- **Success Guarantee:** Approved event is active; digital vouchers are instantiated for all approved attendees with hard expiration dates; balance ledger is initialized.
- **Failure Guarantee:** If any voucher generation step fails, the entire transaction aborts; zero vouchers are created.

---

## UC-SPEC-04: POS Tri-Factor Identity Verification

### Summary
A cashier at an authorized venue validates a physician's identity before unlocking the point-of-sale checkout screen, utilizing one of three production verification channels.

- **Primary Actor:** Vendor Cashier
- **Secondary Actors:** Physician Customer
- **Preconditions:** Cashier is authenticated at an active POS terminal.
- **Trigger:** Physician presents at the counter to settle a dining bill.

### Main Success Scenario (Method 1: QR Code Pass - Primary)
1. Physician presents digital QR pass displayed on their smartphone.
2. Cashier scans the QR code using the optical terminal scanner.
3. System decrypts the unique alphanumeric token and retrieves the matching physician profile.
4. System verifies physician status is active and not soft-deleted.
5. System displays physician photo, name, and specialty on cashier monitor.
6. Cashier confirms visual match and unlocks invoice entry.

### Alternative Scenario A (Method 2: Directory Lookup - Fallback)
1. Physician does not have smartphone or digital pass available.
2. Cashier selects "Directory Lookup" and inputs physician's registered phone number or full name.
3. System searches the verified database and presents matching doctor cards.
4. Cashier verifies the physician's identity against the profile photo and credentials.
5. Cashier selects confirmed profile and unlocks invoice entry.

### Alternative Scenario B (Method 3: Real-Time Email OTP - High Security)
1. Cashier triggers secondary security verification by clicking "Request OTP".
2. System generates a cryptographically secure 6-digit numeric token with a 5-minute validity window.
3. System dispatches OTP via SMTP to physician's verified email address on record.
4. Physician accesses email on mobile device and provides code to cashier.
5. Cashier enters 6-digit code into POS prompt.
6. System verifies code match and temporal validity.
7. System unlocks invoice entry.

### Exception Flows
- **3a. Invalid or Corrupted QR Token:**
  - Scanner reads unrecognized token. System outputs error: "Invalid Digital Pass". Checkout halts.
- **6a (Scenario B). OTP Expired or Mismatched:**
  - Physician provides incorrect or expired code. System rejects input and increments failed attempt counter. After 3 failures, session locks temporarily.

### Postconditions
- **Success Guarantee:** Physician identity is positively verified; cashier terminal displays confirmed aggregate unexpired balance and unlocks billing interface.
- **Failure Guarantee:** Billing interface remains locked; zero customer data is exposed.

---

## UC-SPEC-05: Real-Time Atomic Multi-Voucher Checkout

### Summary
The cashier inputs invoice details, system calculates partner markups if applicable, and atomically liquidates the bill across one or more active vouchers using a waterfall allocation algorithm.

- **Primary Actor:** Vendor Cashier
- **Secondary Actors:** Physician Customer, Venue Administration
- **Preconditions:** Physician identity verified; active unexpired voucher balance exists.
- **Trigger:** Cashier receives dining bill amount from restaurant point-of-sale receipt.

### Main Success Scenario
1. Cashier enters the physical invoice number, billing amount ($AmountSpent$), and dining items description.
2. System queries merchant configuration:
   - If operating at an external partner merchant (Trader), system fetches $ManagementFee\%$ (e.g., $25.00\%$).
   - System computes:
     $$ManagementFeeAmount = AmountSpent \times \left(\frac{ManagementFee\%}{100}\right)$$
     $$TotalDeducted = AmountSpent + ManagementFeeAmount$$
   - If operating at the primary venue, $ManagementFeeAmount = 0$ and $TotalDeducted = AmountSpent$.
3. System initiates an atomic database transaction with pessimistic row-locking on the physician's voucher records.
4. System retrieves all active vouchers where $is\_active = True$ and $expiry\_date \ge CurrentDate$, ordered chronologically by expiration date ascending.
5. System evaluates the cumulative balance:
   $$\sum CurrentBalance \ge TotalDeducted$$
6. System executes the **Waterfall Allocation Algorithm**:
   - Initialized with $RemainingToDeduct = TotalDeducted$.
   - For each voucher in sequence:
     - If $Voucher.current\_balance \le RemainingToDeduct$:
       - $RemainingToDeduct = RemainingToDeduct - Voucher.current\_balance$
       - $Voucher.current\_balance = 0$
     - Else:
       - $Voucher.current\_balance = Voucher.current\_balance - RemainingToDeduct$
       - $RemainingToDeduct = 0$
     - System associates voucher with the transaction in the Many-to-Many junction.
     - Repeat until $RemainingToDeduct = 0$.
7. System generates immutable `Transaction` record storing: gross amount spent, markup percentage, markup amount, total deducted, invoice reference, cashier user ID, and timestamp.
8. Atomic transaction commits to database.
9. POS terminal outputs confirmation receipt showing remaining voucher balance and itemized deduction.

### Exception Flows
- **5a. Insufficient Cumulative Balance (Overdraft Attempt):**
  - If cumulative active balance is less than $TotalDeducted$, system raises a validation exception.
  - Atomic transaction immediately aborts; zero balance is deducted.
  - Cashier is alerted: "Insufficient voucher balance. Available: \$X, Required: \$Y".
- **4a. Expired Voucher Handling:**
  - System encounters vouchers with $expiry\_date < CurrentDate$.
  - Engine strictly ignores expired vouchers; they are excluded from the balance calculation and cannot be debited.

### Postconditions
- **Success Guarantee:** Balances are atomically updated in real time; Many-to-Many junction accurately links all debited vouchers; transaction record is archived for settlement.
- **Failure Guarantee:** Database rolls back completely; zero partial debits occur; vouchers retain exact pre-checkout balances.

---

## UC-SPEC-06: Peer-to-Peer Voucher Balance Transfer

### Summary
An authenticated physician delegates a portion of their active voucher dining balance to a colleague physician, with immediate atomic ledger reallocation and strict audit logging.

- **Primary Actor:** Physician (Sender)
- **Secondary Actors:** Physician (Recipient)
- **Preconditions:** Sender is authenticated; holds an active, unexpired voucher with positive balance.
- **Trigger:** Sender chooses to reallocate dining credits to a colleague.

### Main Success Scenario
1. Physician logs into self-service portal and selects an active voucher.
2. Physician clicks "Transfer Credit".
3. System displays available transferable balance and prompt to select recipient.
4. Physician selects recipient doctor from directory and enters transfer amount ($T$).
5. Physician confirms transfer.
6. System begins atomic transaction and locks sender voucher row.
7. System verifies business invariants:
   - Source voucher is active and $expiry\_date \ge CurrentDate$.
   - Transfer amount satisfies: $0 < T \le SourceVoucher.current\_balance$.
   - Recipient doctor is active and not soft-deleted.
8. System executes balance reallocation:
   - Debits source voucher: $current\_balance = current\_balance - T$.
   - Credits recipient voucher ledger (creating or updating recipient voucher holding identical expiration date to prevent validity extension).
   - Generates immutable `VoucherTransfer` record with sender, recipient, source voucher, and timestamp.
9. Atomic transaction commits.
10. System displays updated balance on sender portal; recipient receives credit immediately.

### Exception Flows
- **7a. Transfer Exceeds Available Balance:**
  - Sender inputs $T > current\_balance$. System blocks submission with error: "Transfer amount exceeds available balance".
- **7b. Attempted Transfer on Expired Voucher:**
  - System detects voucher passed expiration deadline. Operation aborted with error: "Expired vouchers cannot be transferred".

### Postconditions
- **Success Guarantee:** Balances are atomically updated across both accounts; total system liabilities remain unchanged (zero credit creation); transfer audit record is permanently stored.
- **Failure Guarantee:** Transaction rolls back cleanly; no funds leave sender's account.

---

## UC-SPEC-07: End-to-End Vendor Settlement Execution

### Summary
Venue Administrator executes a financial settlement with a partner merchant (Trader), aggregating unsettled transactions, deducting administrative management markups, enforcing balance invariants, and recording payout execution.

- **Primary Actor:** Vendor Admin
- **Secondary Actors:** Partner Merchant Management
- **Preconditions:** Partner merchant has accumulated completed, unsettled POS transactions.
- **Trigger:** Monthly or periodic merchant accounting reconciliation cycle.

### Main Success Scenario
1. Admin opens the Vendor Settlement module and selects the target partner merchant.
2. System aggregates historical sales and computes available solvency:
   $$TotalSales = \sum \text{Historical Transactions for Merchant \& Cashiers}$$
   $$PastSettlements = \sum \text{Completed Settlements for Merchant}$$
   $$AvailableBalance = TotalSales - PastSettlements$$
3. System displays available balance and lists all eligible unsettled transactions.
4. Admin enters the settlement amount ($AmountSettled$) and selects payment date.
5. System verifies the **Solvency Invariant**:
   $$AmountSettled \le AvailableBalance$$
6. Admin selects the batch of transactions being settled.
7. System computes financial totals:
   - **Administrative Commission Retained:** Sum of `management_fee_amount` across selected transactions.
   - **Net Payout to Merchant:** $NetPayout = AmountSettled - AdminCommission$.
8. Admin specifies payment channel (`BANK`, `CASH`, or `CHECK`) and uploads image of signed disbursement receipt / wire transfer slip.
9. Admin clicks "Finalize Settlement".
10. System executes atomic transaction:
    - Creates `VendorSettlement` record with status `COMPLETED`.
    - Associates transactions with settlement via Many-to-Many junction.
    - Flags transactions as settled, preventing inclusion in subsequent settlement batches.
11. System updates merchant balance ledger and generates downloadable settlement statement.

### Exception Flows
- **5a. Settlement Amount Exceeds Solvency Limit:**
  - Admin inputs $AmountSettled > AvailableBalance$.
  - System rejects submission with validation alert: "Settlement amount exceeds available merchant balance. Maximum payable: \$AvailableBalance".
  - Submission is blocked until amount is adjusted.

### Postconditions
- **Success Guarantee:** Transactions are permanently settled; net disbursement is recorded with receipt proof; primary venue's administrative markup is officially booked; merchant balance is updated.
- **Failure Guarantee:** Transactions remain in unsettled pool; no settlement record is created.

---

## UC-SPEC-08: Corporate Sponsor Budget Reconciliation

### Summary
Pharmaceutical corporate sponsor and venue management reconcile total seminar sponsorship commitments against actual doctor dining consumption, identifying unspent balances and closing the sponsorship billing cycle.

- **Primary Actor:** Pharmaceutical Company Representative / Venue Admin
- **Preconditions:** Sponsored seminar has concluded or reached contractual billing date.
- **Trigger:** Close of scientific conference or fiscal sponsorship period.

### Main Success Scenario
1. User navigates to Company Settlement dashboard and selects the pharmaceutical sponsor.
2. System calculates corporate financial balances:
   $$TotalBudgetAllocated = \sum \text{Approved Event Max Budgets}$$
   $$TotalVouchersDistributed = \sum \text{Face Value of Issued Vouchers}$$
   $$TotalAmountSpent = \sum \text{Actual Dining Spend Consumed by Doctors}$$
3. System computes variances:
   - **Unused Budget:** $TotalBudgetAllocated - TotalVouchersDistributed$
   - **Unspent Dining Credit:** $TotalVouchersDistributed - TotalAmountSpent$
4. System presents net corporate payable / refundable balance.
5. Corporate representative and venue administrator agree on final reconciliation figure ($SettlementAmount$).
6. Admin uploads signed corporate memorandum of understanding / wire proof.
7. Status transitions to `COMPLETED` (or `PARTIAL` if milestone payments apply).
8. Corporate sponsorship ledger for the period is officially closed.

### Postconditions
- **Success Guarantee:** Corporate sponsorship commitments are reconciled with penny-level accuracy against actual point-of-sale dining journals.
- **Failure Guarantee:** Incomplete reconciliations remain in `PENDING` state; historical transaction records remain unaltered.

---

## UC-SPEC-09: Delegate Commission Review & Settlement

### Summary
Field sales representatives review seminar performance metrics and receive commission payouts funded by corporate sponsorship agreements.

- **Primary Actor:** Medical Delegate / Venue Admin
- **Preconditions:** Assigned medical seminars have concluded.
- **Trigger:** Monthly delegate compensation cycle.

### Main Success Scenario
1. Delegate logs into the Delegate Settlement portal.
2. System aggregates performance metrics:
   - Count of completed sponsored seminars assigned to delegate ($EventsAssigned$).
   - Count of verified attending physicians registered ($DoctorsRegistered$).
   - Contracted commission rate percentage ($CommissionRate\%$).
3. System computes commission payout:
   $$TotalCommission = Function(EventsAssigned, DoctorsRegistered) \times CommissionRate$$
4. Delegate reviews figures and confirms performance statement.
5. Venue administrator verifies performance logs, enters payout amount ($SettlementAmount$), selects payment date, and attaches payment confirmation slip.
6. System marks settlement status as `COMPLETED`.
7. Audit log is updated.

### Extensions & Alternative Flows
- **4a. Commission Dispute:**
  - Delegate disputes attendee count or commission tier.
  - Status transitions to `DISPUTED`. Payout is placed on hold until event attendance logs are audited and reconciled.

### Postconditions
- **Success Guarantee:** Representative compensation is verified, documented with receipt proof, and archived in the financial ledger.
- **Failure Guarantee:** Disputed payouts remain locked until mutually authorized.
