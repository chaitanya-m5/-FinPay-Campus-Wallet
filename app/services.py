from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import extract
from . import models

BASE_RULES = {
    "CANTEEN": {"rate_bps": 200, "cap_paise": 5000},
    "STATIONERY": {"rate_bps": 100, "cap_paise": 2000},
    "TRANSPORT": {"rate_bps": 300, "cap_paise": 10000},
    "HOSTEL": {"rate_bps": 50, "cap_paise": 20000},
    "ONLINE": {"rate_bps": 100, "cap_paise": 3000},
    "TOP_UP": {"rate_bps": 0, "cap_paise": 0},
}
TIER_MULTIPLIERS = {"BASIC": (1, 1), "PRIME": (3, 2), "PREMIUM": (2, 1)}

def calculate_cashback(amount_paise: int, category: str, tier: str) -> int:
    rule = BASE_RULES[category]
    numerator, denominator = TIER_MULTIPLIERS[tier]
    return (amount_paise * rule["rate_bps"] * numerator) // (10000 * denominator)

def get_monthly_cashback(db: Session, user_id: int, category: str, now=None) -> int:
    now = now or datetime.utcnow()
    rows = db.query(models.Transaction.cashback_paise).filter(
        models.Transaction.user_id == user_id,
        models.Transaction.category == category,
        models.Transaction.status == "SUCCESS",
        extract("year", models.Transaction.created_at) == now.year,
        extract("month", models.Transaction.created_at) == now.month,
    ).all()
    return sum(row[0] for row in rows)

def process_payment(db: Session, user: models.User, merchant_name: str, category: str,
                    amount_paise: int, idempotency_key: str):
    existing = db.query(models.Transaction).filter_by(idempotency_key=idempotency_key).first()
    if existing:
        if existing.user_id != user.id:
            raise ValueError("Idempotency key has already been used")
        return existing, True
    if amount_paise <= 0:
        raise ValueError("Payment amount must be positive")
    if user.wallet_balance_paise < amount_paise:
        raise ValueError("Insufficient wallet balance")
    raw = calculate_cashback(amount_paise, category, user.tier)
    rule = BASE_RULES[category]
    cap_num, cap_den = TIER_MULTIPLIERS[user.tier]
    monthly_cap = (rule["cap_paise"] * cap_num) // cap_den
    already_earned = get_monthly_cashback(db, user.id, category)
    cashback = min(raw, max(0, monthly_cap - already_earned))
    user.wallet_balance_paise -= amount_paise
    user.wallet_balance_paise += cashback
    tx = models.Transaction(user_id=user.id, merchant_name=merchant_name, category=category,
        amount_paise=amount_paise, raw_cashback_paise=raw, cashback_paise=cashback,
        idempotency_key=idempotency_key, status="SUCCESS")
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx, False
