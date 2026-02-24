from pydantic import BaseModel
from typing import Any


class PaystackCustomer(BaseModel):
    email: str
    id: int | None = None
    customer_code: str | None = None


class PaystackData(BaseModel):
    reference: str
    amount: int  # in kobo
    currency: str = "NGN"
    status: str
    customer: PaystackCustomer
    metadata: dict[str, Any] | None = None


class PaystackEvent(BaseModel):
    event: str
    data: PaystackData
