from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import extract, func, text
from .database import Base, engine, get_db, SessionLocal
from . import models, schemas
from .security import hash_password, verify_password, create_access_token, get_current_user, require_roles
from .services import BASE_RULES, TIER_MULTIPLIERS, process_payment

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app = FastAPI(title="FinPay Campus Wallet API", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

student_user = Depends(require_roles("STUDENT"))
company_user = Depends(require_roles("COMPANY"))
coordinator_user = Depends(require_roles("PLACEMENT_COORDINATOR"))


def migrate_user_role_column():
    # SQLAlchemy create_all does not add columns to an existing SQLite table.
    with engine.begin() as connection:
        columns = connection.execute(text("PRAGMA table_info(users)")).fetchall()
        if "role" not in {column[1] for column in columns}:
            connection.execute(text(
                "ALTER TABLE users ADD COLUMN role VARCHAR(30) NOT NULL DEFAULT 'STUDENT'"
            ))


def seed_demo_users():
    demo_users = [
        ("rahul", "Rahul Sharma", "rahul123", "STUDENT", 100000, "BASIC"),
        ("priya", "Priya Rao", "priya123", "STUDENT", 150000, "PRIME"),
        ("company", "Campus Merchant", "company123", "COMPANY", 0, "BASIC"),
        ("coordinator", "Placement Coordinator", "coordinator123",
         "PLACEMENT_COORDINATOR", 0, "BASIC"),
    ]
    db = SessionLocal()
    try:
        for username, full_name, password, role, balance, tier in demo_users:
            user = db.query(models.User).filter_by(username=username).first()
            if user is None:
                db.add(models.User(
                    username=username, full_name=full_name,
                    password_hash=hash_password(password), role=role,
                    wallet_balance_paise=balance, tier=tier
                ))
            else:
                # Preserve existing credentials and balances while assigning the demo role.
                user.role = role
        db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    migrate_user_role_column()
    seed_demo_users()


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "application": "FinPay", "version": "1.1.0"}


@app.post("/api/auth/login")
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(username=payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return {
        "access_token": create_access_token(user.id),
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username,
                 "full_name": user.full_name, "role": user.role}
    }


@app.get("/api/auth/me")
def current_user_profile(user: models.User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "full_name": user.full_name,
            "role": user.role, "tier": user.tier}


@app.get("/api/wallet")
def wallet(user: models.User = student_user):
    mult = TIER_MULTIPLIERS[user.tier]
    return {"id": user.id, "full_name": user.full_name, "username": user.username,
            "balance_paise": user.wallet_balance_paise,
            "balance_rupees": user.wallet_balance_paise / 100,
            "tier": user.tier, "tier_multiplier": mult[0] / mult[1],
            "role": user.role}


@app.get("/api/rules")
def rules(user: models.User = student_user):
    return {
        "categories": {k: {"basic_rate_percent": v["rate_bps"] / 100,
                           "basic_monthly_cap_paise": v["cap_paise"],
                           "basic_monthly_cap_rupees": v["cap_paise"] / 100}
                       for k, v in BASE_RULES.items()},
        "tier_multipliers": {k: {"cashback_rate": n / d, "monthly_cap": n / d}
                             for k, (n, d) in TIER_MULTIPLIERS.items()}
    }


def serialize(tx):
    return {"id": tx.id, "merchant_name": tx.merchant_name, "category": tx.category,
            "amount_paise": tx.amount_paise, "amount_rupees": tx.amount_paise / 100,
            "raw_cashback_paise": tx.raw_cashback_paise,
            "raw_cashback_rupees": tx.raw_cashback_paise / 100,
            "cashback_paise": tx.cashback_paise,
            "cashback_rupees": tx.cashback_paise / 100,
            "status": tx.status, "created_at": tx.created_at.isoformat()}


@app.post("/api/payments")
def pay(payload: schemas.PaymentRequest, db: Session = Depends(get_db),
        user: models.User = student_user):
    amount_paise = int(round(payload.amount_rupees * 100))
    try:
        tx, duplicate = process_payment(db, user, payload.merchant_name, payload.category,
                                        amount_paise, payload.idempotency_key)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    return {"message": "Previously processed payment returned" if duplicate else "Payment successful",
            "duplicate_request": duplicate, "transaction": serialize(tx)}


@app.get("/api/transactions")
def transactions(limit: int = 50, db: Session = Depends(get_db),
                 user: models.User = student_user):
    rows = db.query(models.Transaction).filter_by(user_id=user.id).order_by(
        models.Transaction.created_at.desc()).limit(min(max(limit, 1), 100)).all()
    return [serialize(tx) for tx in rows]


@app.get("/api/reconciliation")
def reconciliation(db: Session = Depends(get_db), user: models.User = student_user):
    now = datetime.utcnow()
    rows = db.query(models.Transaction).filter(
        models.Transaction.user_id == user.id,
        extract("year", models.Transaction.created_at) == now.year,
        extract("month", models.Transaction.created_at) == now.month
    ).all()
    spend = sum(t.amount_paise for t in rows)
    cashback = sum(t.cashback_paise for t in rows)
    by_category = {cat: sum(t.cashback_paise for t in rows if t.category == cat)
                   for cat in BASE_RULES}
    return {"year": now.year, "month": now.month, "transaction_count": len(rows),
            "total_spend_paise": spend, "total_spend_rupees": spend / 100,
            "total_cashback_paise": cashback, "total_cashback_rupees": cashback / 100,
            "cashback_by_category": {k: {"earned_paise": v, "earned_rupees": v / 100}
                                     for k, v in by_category.items()}}


@app.put("/api/wallet/tier")
def change_tier(payload: schemas.TierRequest, db: Session = Depends(get_db),
                user: models.User = student_user):
    user.tier = payload.tier
    db.commit()
    return {"message": "Wallet tier updated", "tier": user.tier}


@app.get("/api/company/summary")
def company_summary(db: Session = Depends(get_db), user: models.User = company_user):
    totals = db.query(func.count(models.Transaction.id),
                      func.coalesce(func.sum(models.Transaction.amount_paise), 0),
                      func.coalesce(func.sum(models.Transaction.cashback_paise), 0)).one()
    return {"role": user.role, "workspace": "Company",
            "transaction_count": totals[0],
            "total_payment_volume_paise": int(totals[1]),
            "total_cashback_paise": int(totals[2])}


@app.get("/api/coordinator/summary")
def coordinator_summary(db: Session = Depends(get_db),
                        user: models.User = coordinator_user):
    students = db.query(func.count(models.User.id)).filter(
        models.User.role == "STUDENT").scalar() or 0
    companies = db.query(func.count(models.User.id)).filter(
        models.User.role == "COMPANY").scalar() or 0
    totals = db.query(func.count(models.Transaction.id),
                      func.coalesce(func.sum(models.Transaction.amount_paise), 0),
                      func.coalesce(func.sum(models.Transaction.cashback_paise), 0)).one()
    return {"role": user.role, "workspace": "Placement Coordinator",
            "student_accounts": students, "company_accounts": companies,
            "transaction_count": totals[0],
            "total_payment_volume_paise": int(totals[1]),
            "total_cashback_paise": int(totals[2])}
