# Operational Workflows & Engineering Flowcharts

This document details the operational workflows, business process flowcharts, activity diagrams, and sequence diagrams governing the **Vaetcher** platform. 

Every diagram is derived from production-validated business logic, illustrating end-to-end interactions between physicians, cashiers, venue administrators, corporate sponsors, and financial settlement engines.

---

## 1. Workflow 1: Medical Seminar Sponsorship & Voucher Generation

This workflow details how a pharmaceutical sponsor initiates a medical seminar, allocates attendee budgets, gains venue approval, and triggers automatic digital voucher creation.

### 1.1. Sequence Diagram
```mermaid
sequenceDiagram
    autonumber
    actor Sponsor as Pharma Sponsor / Delegate
    actor Admin as Venue Admin
    participant Portal as Event Request Service
    participant Engine as Voucher Issuance Engine
    participant DB as Relational Database
    actor Doctor as Attending Doctor

    Sponsor->>Portal: Submit Event Request (Title, Date, Budget Model, Doctors)
    Note over Sponsor,Portal: Model A: Per-Doctor Allowance<br/>Model B: Lump-Sum Budget Cap
    Portal->>DB: Persist Event Request (Status = PENDING)
    Portal-->>Admin: Dispatch Pending Approval Notification
    Admin->>Portal: Inspect Event Details & Financial Solvency
    Admin->>Portal: Approve Event & Confirm Voucher Expiry Days
    Portal->>Engine: Trigger Event Activation (Event ID)
    Engine->>DB: Transition Event Status -> APPROVED
    loop For Each Registered Physician
        Engine->>Engine: Calculate Expiry Date = Current Date + Expiry Days
        Engine->>DB: Instantiate Voucher Record (Initial Balance, Current Balance, Expiry Date)
    end
    DB-->>Engine: Creation Confirmed
    Engine-->>Doctor: Digital Pass Available on Mobile Portal
    Portal-->>Admin: Event Active & Vouchers Issued
```

### 1.2. Process Flowchart
```mermaid
flowchart TD
    Start([Sponsor Submits Seminar Request]) --> CheckModel{Select Allocation Model}
    CheckModel -->|Model A| PerDoctor[Define Individual Allowance per Doctor]
    CheckModel -->|Model B| LumpSum[Define Global Seminar Budget Cap]
    
    PerDoctor --> Submit[Submit Roster to Venue Admin]
    LumpSum --> Submit
    
    Submit --> AdminReview{Admin Reviews Request}
    AdminReview -->|Rejected| Terminate([Request Rejected & Sponsor Notified])
    AdminReview -->|Approved| SetExpiry[Confirm Voucher Expiry Window e.g. 90 Days]
    
    SetExpiry --> CreateEvent[Create Approved Event Record]
    CreateEvent --> IterateDoctors[Iterate Through Invited Physicians]
    IterateDoctors --> CalcExpiry[Compute Hard Expiration Date]
    CalcExpiry --> IssueVoucher[Generate Digital Voucher Record]
    IssueVoucher --> MoreDoctors{More Doctors in Roster?}
    MoreDoctors -->|Yes| IterateDoctors
    MoreDoctors -->|No| ActivatePasses([All Doctor Passes Active on Mobile Portal])
```

---

## 2. Workflow 2: POS Checkout & Tri-Factor Verification

Illustrates the cashier point-of-sale workflow for validating a physician's identity via one of three available verification pathways before unlocking invoice entry.

```mermaid
flowchart TD
    CustomerArrives([Doctor Arrives at Checkout Counter]) --> CashierPrompt[Cashier Opens POS Terminal]
    CashierPrompt --> SelectMethod{Select Verification Channel}

    %% Method 1: QR Code
    SelectMethod -->|Method 1: Primary| ScanQR[Scan Doctor QR Pass]
    ScanQR --> ReadToken[Read Alphanumeric Token]
    ReadToken --> LookupToken{Token Matches Active Doctor?}
    LookupToken -->|No| ErrorQR[Display Token Error] --> TerminatePOS([Abort Checkout])
    LookupToken -->|Yes| FetchProfile[Load Doctor Record]

    %% Method 2: Search Directory
    SelectMethod -->|Method 2: Directory| InputSearch[Input Doctor Phone or Name]
    InputSearch --> QueryDirectory[Search Active Database]
    QueryDirectory --> MatchFound{Match Found?}
    MatchFound -->|No| ErrorSearch[No Physician Found] --> TerminatePOS
    MatchFound -->|Yes| ConfirmIdentity[Cashier Confirms Portrait & Specialty]
    ConfirmIdentity --> FetchProfile

    %% Method 3: Real-Time OTP
    SelectMethod -->|Method 3: OTP| TriggerOTP[Cashier Clicks 'Send OTP']
    TriggerOTP --> GenCode[Generate 6-Digit Dynamic Code]
    GenCode --> DispatchMail[SMTP Mail Dispatched to Doctor Email]
    DispatchMail --> DoctorChecks[Doctor Reads Code from Inbox]
    DoctorChecks --> CashierInputs[Cashier Enters Code in POS]
    CashierInputs --> VerifyCode{Code Valid & Not Expired?}
    VerifyCode -->|No| ErrorOTP[Invalid / Expired OTP] --> TerminatePOS
    VerifyCode -->|Yes| FetchProfile

    %% Post Verification Checks
    FetchProfile --> CheckVouchers[Query Doctor Active Vouchers]
    CheckVouchers --> FilterVouchers[Filter: is_active = True AND Expiry Date >= Today]
    FilterVouchers --> HasBalance{Total Active Balance > 0?}
    HasBalance -->|No| NoBalanceError[Display Zero/Expired Balance] --> TerminatePOS
    HasBalance -->|Yes| UnlockInvoice[Unlock Billing & Invoice Entry Screen]
```

---

## 3. Workflow 3: Multi-Voucher Waterfall Deduction & Partner Markup Engine

This diagram outlines the core atomic calculation executed when an invoice is submitted, demonstrating the Many-to-Many deduction model across multiple vouchers and dynamic partner markups.

### 3.1. Waterfall Deduction Sequence Diagram
```mermaid
sequenceDiagram
    autonumber
    actor Cashier as Cashier
    participant Terminal as POS Register
    participant Calc as Dynamic Markup Engine
    participant Waterfall as Waterfall Allocation Engine
    participant DB as Relational Database

    Cashier->>Terminal: Enter Invoice No, Gross Bill ($100.00), Items
    Terminal->>Calc: Evaluate Transaction (Merchant ID, Gross Bill)
    alt Merchant is External Partner (Trader)
        Calc->>Calc: Fetch Partner Markup % (e.g., 25.00%)
        Calc->>Calc: Management Fee = $100.00 * 25% = $25.00
        Calc->>Calc: Total Deducted = $100.00 + $25.00 = $125.00
    else Merchant is Primary Venue
        Calc->>Calc: Management Fee = $0.00
        Calc->>Calc: Total Deducted = $100.00
    end
    Calc-->>Terminal: Total Required Deduction

    Terminal->>Waterfall: Request Deduction (Doctor ID, Total Required)
    Waterfall->>DB: Begin Atomic Transaction & Lock Doctor Vouchers
    Waterfall->>DB: Fetch Active Unexpired Vouchers (ORDER BY Expiry Date ASC)
    
    alt Cumulative Balance < Total Required
        Waterfall-->>Terminal: Invariant Failed: Insufficient Balance
        Terminal-->>Cashier: Display Overdraft Error (Transaction Aborted)
    else Cumulative Balance >= Total Required
        loop While Remaining Deduction > 0
            Waterfall->>Waterfall: Inspect Voucher[i] Available Balance
            alt Voucher[i] Balance <= Remaining Deduction
                Waterfall->>Waterfall: Deduct Full Voucher Balance (Voucher[i] -> 0)
                Waterfall->>Waterfall: Remaining Deduction = Remaining Deduction - Voucher[i] Balance
                Waterfall->>DB: Update Voucher[i] Balance = 0
            else Voucher[i] Balance > Remaining Deduction
                Waterfall->>Waterfall: Deduct Remaining Deduction from Voucher[i]
                Waterfall->>DB: Update Voucher[i] Balance = (Voucher[i] Balance - Remaining Deduction)
                Waterfall->>Waterfall: Remaining Deduction = 0
            end
            Waterfall->>DB: Associate Voucher[i] with Transaction (M2M)
        end
        Waterfall->>DB: Insert Transaction Record
        Waterfall->>DB: Commit Atomic Transaction
        Waterfall-->>Terminal: Transaction Approved & Receipt Generated
        Terminal-->>Cashier: Print Confirmation Slip
    end
```

### 3.2. Algorithmic Flowchart
```mermaid
flowchart TD
    SubmitBill([Cashier Submits Bill]) --> IsPartner{Is Partner Venue?}
    IsPartner -->|Yes| ApplyMarkup[Markup = Bill * ManagementFee%<br/>TotalDebit = Bill + Markup]
    IsPartner -->|No| ZeroMarkup[Markup = $0.00<br/>TotalDebit = Bill]

    ApplyMarkup --> StartAtomic[Start Atomic Transaction & Lock Records]
    ZeroMarkup --> StartAtomic

    StartAtomic --> QueryVouchers[Fetch Doctor Vouchers: is_active=True, Expiry>=Today<br/>Sort by Expiry ASC]
    QueryVouchers --> CheckTotal{Sum of Balances >= TotalDebit?}
    CheckTotal -->|No| Rollback[Rollback Transaction & Display Insufficient Balance] --> EndFail([Transaction Aborted])

    CheckTotal -->|Yes| InitLoop[Set RemainingToDeduct = TotalDebit]
    InitLoop --> GetNextVoucher[Select Next Expiring Voucher]
    GetNextVoucher --> CompareBalance{Voucher Balance <= RemainingToDeduct?}

    CompareBalance -->|Yes| ConsumeAll[Deduct Entire Voucher Balance<br/>RemainingToDeduct = RemainingToDeduct - Voucher Balance<br/>Set Voucher Balance = 0]
    CompareBalance -->|No| ConsumePartial[Voucher Balance = Voucher Balance - RemainingToDeduct<br/>RemainingToDeduct = 0]

    ConsumeAll --> LinkM2M[Link Voucher to Transaction Junction]
    ConsumePartial --> LinkM2M

    LinkM2M --> CheckRemaining{RemainingToDeduct == 0?}
    CheckRemaining -->|No| GetNextVoucher
    CheckRemaining -->|Yes| SaveTransaction[Insert Transaction with Vouchers M2M]
    SaveTransaction --> CommitDB[Commit Transaction to Database]
    CommitDB --> Success([Receipt Printed & Balances Updated])
```

---

## 4. Workflow 4: Peer-to-Peer Voucher Balance Transfer

Governs the delegation of dining allowances between attending physicians, enforcing ownership, balance limits, and chronological expiration inheritance.

```mermaid
sequenceDiagram
    autonumber
    actor Sender as Transferring Physician
    participant Portal as Doctor Portal
    participant Engine as Transfer Engine
    participant DB as Relational Database
    actor Receiver as Beneficiary Physician

    Sender->>Portal: Select Active Voucher & Click 'Transfer Balance'
    Portal->>DB: Query Active Unexpired Vouchers for Sender
    DB-->>Portal: List Available Vouchers & Current Balances
    Sender->>Portal: Enter Recipient Doctor & Transfer Amount ($T)
    Portal->>Engine: Submit Transfer Request (Voucher ID, Recipient ID, $T)
    
    Engine->>DB: Begin Atomic Transaction
    Engine->>DB: Lock Source Voucher Record
    
    alt Voucher Expired OR is_active == False
        Engine-->>Portal: Validation Error: Voucher Inactive or Expired
        Portal-->>Sender: Display Rejection
    else Transfer Amount $T > Current Balance
        Engine-->>Portal: Validation Error: Transfer Exceeds Balance
        Portal-->>Sender: Display Insufficient Balance
    else Recipient ID Invalid OR Soft-Deleted
        Engine-->>Portal: Validation Error: Recipient Not Found
        Portal-->>Sender: Display Invalid Recipient
    else All Invariants Satisfied
        Engine->>DB: Debit Source Voucher: current_balance = current_balance - $T
        Engine->>DB: Credit Recipient Voucher Account (Same Expiry Constraints)
        Engine->>DB: Insert Immutable VoucherTransfer Audit Record
        Engine->>DB: Commit Atomic Transaction
        Engine-->>Portal: Transfer Confirmed
        Portal-->>Sender: Display Updated Balance
        Portal-->>Receiver: Credit Added to Portfolio
    end
```

---

## 5. Workflow 5: Vendor Settlement End-to-End Reconciliation

Details how venue administrators close financial periods with partner dining merchants (Traders), deducting administrative management fees and enforcing balance invariants.

```mermaid
flowchart TD
    AdminStarts([Admin Opens Vendor Settlement Module]) --> SelectMerchant[Select Partner Merchant]
    SelectMerchant --> QuerySales[Aggregate All Historical Sales for Merchant & Cashiers]
    QuerySales --> QueryPastSettlements[Aggregate All Completed Past Settlements]
    QueryPastSettlements --> ComputeSolvency[Compute Available Solvency:<br/>AvailableBalance = TotalSales - PastSettlements]

    ComputeSolvency --> DisplayUnsettled[Display Unsettled Transactions Pool]
    DisplayUnsettled --> AdminInputs[Admin Enters Settlement Amount & Date]
    AdminInputs --> ValidateSolvency{Settlement Amount <= AvailableBalance?}

    ValidateSolvency -->|No| RejectAmount[Display Error: Exceeds Available Balance] --> AdminInputs
    ValidateSolvency -->|Yes| SelectTransactions[Select Transactions Covered in Batch]
    
    SelectTransactions --> CalcAdminMarkup[Compute Total Admin Commission Retained:<br/>AdminCommission = Sum of Management Fee Amounts]
    CalcAdminMarkup --> CalcNetMerchant[Compute Net Merchant Payout:<br/>NetPayout = AmountSettled - AdminCommission]
    
    CalcNetMerchant --> ChoosePayment[Select Disbursement Channel: Bank / Cash / Check]
    ChoosePayment --> UploadReceipt[Upload Signed Receipt / Transfer Slip]
    UploadReceipt --> ConfirmSettlement[Admin Submits Settlement as COMPLETED]

    ConfirmSettlement --> StartDBSettlement[Start Atomic DB Transaction]
    StartDBSettlement --> InsertSettlement[Create VendorSettlement Record]
    InsertSettlement --> LinkTransactionsM2M[Link Transactions to Settlement M2M]
    LinkTransactionsM2M --> LockSettled[Flag Transactions as Settled]
    LockSettled --> CommitSettlement[Commit to Database]
    CommitSettlement --> PayoutComplete([Disbursement Finalized & Audit Closed])
```

---

## 6. Workflow 6: Pharmaceutical Company Budget Settlement

Governs the corporate reconciliation between sponsoring pharmaceutical firms and the hospitality venue, calculating budget utilization and surplus credits.

```mermaid
flowchart TD
    PeriodEnd([Corporate Billing Cycle / Event Concluded]) --> OpenCompanySettlement[Open Company Settlement View]
    OpenCompanySettlement --> SelectCompany[Select Pharmaceutical Sponsor]
    
    SelectCompany --> AggregateBudget[Sum Total Approved Event Budgets: TotalBudget]
    AggregateBudget --> AggregateVouchers[Sum Total Distributed Vouchers: TotalVouchers]
    AggregateVouchers --> AggregateDining[Sum Total Dining Spend Consumed: TotalSpent]

    AggregateDining --> CalcSurplus[Compute Financial Variances:<br/>UnallocatedBudget = TotalBudget - TotalVouchers<br/>UnspentPhysicianCredit = TotalVouchers - TotalSpent]

    CalcSurplus --> DetermineSettlement[Calculate Net Settlement Amount Due]
    DetermineSettlement --> ReviewStatus{Sponsor Reviews Statement}
    
    ReviewStatus -->|Disputed| MarkPending[Set Status = PENDING / Requires Audit] --> ReconcileLines[Reconcile Individual Invoices] --> ReviewStatus
    ReviewStatus -->|Partial Payment| MarkPartial[Set Status = PARTIAL & Upload Partial Slip] --> ReconcileRemaining([Balance Carried Forward])
    ReviewStatus -->|Full Payment| MarkCompleted[Set Status = COMPLETED & Upload Corporate Slip] --> CloseCorporateLedger([Corporate Account Reconciled])
```

---

## 7. Workflow 7: Medical Delegate Commission Settlement

Details the commission calculation and payout authorization for field representatives coordinating scientific seminars.

```mermaid
flowchart TD
    StartDelegate([Representative Commission Review]) --> SelectDelegate[Select Medical Sales Delegate]
    SelectDelegate --> SelectSponsor[Select Associated Pharma Sponsor]

    SelectSponsor --> AggregateEvents[Count Completed Events Assigned]
    AggregateEvents --> AggregateDoctors[Count Registered Attending Physicians]
    AggregateDoctors --> GetRate[Retrieve Contracted Commission Rate %]

    GetRate --> ComputeCommission[Calculate Performance Remuneration:<br/>TotalCommission = Formula(Events, Doctors, CommissionRate)]

    ComputeCommission --> AdminDelegateReview{Review Performance Metrics}
    AdminDelegateReview -->|Dispute| FlagDisputed[Set Status = DISPUTED / Under Review] --> TerminateReview([Hold Payout])
    AdminDelegateReview -->|Approved| EnterPayout[Set Settlement Amount & Date]
    EnterPayout --> AttachSlip[Upload Payment Voucher / Receipt]
    AttachSlip --> SetCompleted[Transition Status to COMPLETED]
    SetCompleted --> DelegatePaid([Delegate Remuneration Disbursed])
```
