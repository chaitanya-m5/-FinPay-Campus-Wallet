# FinPay Campus Wallet

FastAPI + SQLite demo based on the FinPay scenario.

## Run (Windows PowerShell)
```powershell
cd FinPay_Website
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000. API docs: http://127.0.0.1:8000/docs

Demo accounts: `rahul / rahul123` and `priya / priya123`.

## Included
- Responsive student wallet dashboard
- JWT demo login
- Payments and transaction history
- BASIC / PRIME / PREMIUM tiers
- Cashback by merchant category and monthly category caps
- Integer-paise cashback arithmetic
- Idempotency keys to prevent duplicate processing
- Monthly reconciliation summary

## Scenario rules
BASIC: Canteen 2% / ₹50 cap; Stationery 1% / ₹20; Transport 3% / ₹100; Hostel 0.5% / ₹200; Online 1% / ₹30; Top-up 0% / no cashback.
Tier multipliers: BASIC 1x, PRIME 1.5x, PREMIUM 2x.

## Important
The scenario says to reuse TalentHub's JWT infrastructure. Since that code was not supplied, this standalone demo includes a simple JWT login. Replace it with TalentHub's existing authentication when integrating. Change the demo secret and credentials before deployment. This is an educational simulation, not a real payment gateway.
