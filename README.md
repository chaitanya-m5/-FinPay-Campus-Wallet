# FinPay Campus Wallet

FastAPI + SQLite campus wallet demo with JWT authentication, role-based access control, payments and cashback.

## Run (Windows PowerShell)

```powershell
py -m venv venv
.\\venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. API docs: http://127.0.0.1:8000/docs

## Demo accounts

| Role | Username | Password |
|---|---|---|
| Student (BASIC) | `rahul` | `rahul123` |
| Student (PRIME) | `priya` | `priya123` |
| Company | `company` | `company123` |
| Placement Coordinator | `coordinator` | `coordinator123` |

Change demo credentials and the JWT secret before deployment.

## Role-based access

- **Student:** wallet balance, payments, transaction history, cashback rules and personal monthly reconciliation.
- **Company:** aggregate payment activity only; student identities and individual wallet records are not exposed.
- **Placement Coordinator:** high-level account and transaction totals for monitoring.
- Roles are read from the stored account after login. The login request does not accept a role, so a client cannot self-promote.
- Student wallet/payment endpoints reject Company and Placement Coordinator accounts with HTTP 403.

## API highlights

- `POST /api/auth/login` — obtain a JWT.
- `GET /api/auth/me` — authenticated account and role.
- `GET /api/company/summary` — Company-only aggregate dashboard data.
- `GET /api/coordinator/summary` — Placement Coordinator-only summary.
- `GET /api/wallet`, `POST /api/payments`, `GET /api/transactions` — Student-only wallet operations.

## Dependency compatibility

Passlib 1.7.4 expects a bcrypt interface that changed in newer bcrypt releases. The explicit `bcrypt==4.0.1` pin keeps the existing Passlib-based password hashing compatible. Install exact versions with `pip install -r requirements.txt`.

## Existing database migration

At startup, FinPay checks whether the SQLite `users` table already has a `role` column. If not, it adds the column with a default of `STUDENT`, preserving existing users, password hashes, balances and transaction history.

## Existing FinPay features

- Responsive student wallet dashboard
- JWT login and database-backed role authorization
- Payments and transaction history
- BASIC / PRIME / PREMIUM tiers
- Cashback by merchant category and monthly category caps
- Integer-paise cashback arithmetic
- Idempotency keys to prevent duplicate processing
- Monthly reconciliation summary

## Scenario rules

BASIC: Canteen 2% / ₹50 cap; Stationery 1% / ₹20; Transport 3% / ₹100; Hostel 0.5% / ₹200; Online 1% / ₹30; Top-up 0% / no cashback.

Tier multipliers: BASIC 1x, PRIME 1.5x, PREMIUM 2x.

This is an educational simulation, not a real payment gateway or a complete placement-management system.
