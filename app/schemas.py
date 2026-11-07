from pydantic import BaseModel, Field
from typing import Literal

Category = Literal["CANTEEN", "STATIONERY", "TRANSPORT", "HOSTEL", "ONLINE", "TOP_UP"]
Tier = Literal["BASIC", "PRIME", "PREMIUM"]

class LoginRequest(BaseModel):
    username: str
    password: str

class PaymentRequest(BaseModel):
    merchant_name: str = Field(min_length=2, max_length=100)
    category: Category
    amount_rupees: float = Field(gt=0, le=100000)
    idempotency_key: str = Field(min_length=8, max_length=100)

class TierRequest(BaseModel):
    tier: Tier
