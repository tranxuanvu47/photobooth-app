from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
import asyncio
import uvicorn

app = FastAPI(title="Photobooth Mock Payment Server")

# In-memory database
# key: order_id, value: payment data
db: Dict[str, dict] = {}

# Pydantic models
class PaymentCreate(BaseModel):
    package_id: str
    amount: int
    description: Optional[str] = None

class PaymentResponse(BaseModel):
    order_id: str
    amount: int
    status: str
    qr_code: str
    payment_url: str
    expires_at: datetime
    created_at: datetime

class PaymentStatusResponse(BaseModel):
    order_id: str
    status: str
    amount: int
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    expires_at: datetime

class SimulateRequest(BaseModel):
    action: str  # "paid" | "failed" | "expired" | "pending"

class SimulateDelayedRequest(BaseModel):
    delay_seconds: int

class PhotoboothStartRequest(BaseModel):
    order_id: str

# Helper function to check and update expiration
def update_order_status(order_id: str):
    order = db.get(order_id)
    if not order:
        return None
    
    # If pending, check if it should be expired
    if order["status"] == "pending":
        if datetime.now() > order["expires_at"]:
            order["status"] = "expired"
    
    return order

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/orders")
def get_all_orders():
    """Debug endpoint to see all orders"""
    return list(db.values())

@app.post("/payments/create", response_model=PaymentResponse)
def create_payment(payment: PaymentCreate):
    order_id = str(uuid.uuid4())[:8].upper() # 8-character ID for simplicity
    now = datetime.now()
    expires_at = now + timedelta(minutes=5)
    
    order = {
        "order_id": order_id,
        "package_id": payment.package_id,
        "amount": payment.amount,
        "description": payment.description,
        "status": "pending",
        "qr_code": f"PAYMENT://order_id={order_id}&amount={payment.amount}",
        "payment_url": f"http://localhost:8000/mock-pay/{order_id}",
        "expires_at": expires_at,
        "created_at": now,
        "transaction_id": None,
        "paid_at": None
    }
    
    db[order_id] = order
    return order

@app.get("/payments/{order_id}/status", response_model=PaymentStatusResponse)
def get_payment_status(order_id: str):
    order = update_order_status(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_id": order["order_id"],
        "status": order["status"],
        "amount": order["amount"],
        "transaction_id": order.get("transaction_id"),
        "paid_at": order.get("paid_at"),
        "expires_at": order["expires_at"]
    }

@app.post("/payments/{order_id}/simulate")
def simulate_payment(order_id: str, request: SimulateRequest):
    order = db.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    action = request.action.lower()
    
    if action == "paid":
        if order["status"] == "paid":
            return order # Already paid
        order["status"] = "paid"
        order["transaction_id"] = f"TXN-{uuid.uuid4().hex[:10].upper()}"
        order["paid_at"] = datetime.now()
    elif action == "failed":
        order["status"] = "failed"
    elif action == "expired":
        order["status"] = "expired"
    elif action == "pending":
        order["status"] = "pending"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    return order

async def delayed_payment_task(order_id: str, delay: int):
    await asyncio.sleep(delay)
    order = db.get(order_id)
    if order and order["status"] == "pending":
        # Check expiration again just in case
        if datetime.now() <= order["expires_at"]:
            order["status"] = "paid"
            order["transaction_id"] = f"TXN-DELAYED-{uuid.uuid4().hex[:10].upper()}"
            order["paid_at"] = datetime.now()
            print(f"Order {order_id} has been automatically paid after {delay} seconds.")
        else:
            order["status"] = "expired"
            print(f"Order {order_id} expired before delayed payment could occur.")

@app.post("/payments/{order_id}/simulate-delayed-paid")
def simulate_delayed_paid(order_id: str, request: SimulateDelayedRequest, background_tasks: BackgroundTasks):
    order = db.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot pay order with status: {order['status']}")
    
    background_tasks.add_task(delayed_payment_task, order_id, request.delay_seconds)
    return {"message": f"Order {order_id} will be set to 'paid' after {request.delay_seconds} seconds if still pending."}

@app.post("/photobooth/start")
def start_photobooth(request: PhotoboothStartRequest):
    order_id = request.order_id
    order = update_order_status(order_id) # Check expiration too
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] != "paid":
        raise HTTPException(status_code=403, detail=f"Payment not completed. Current status: {order['status']}")
    
    # Logic for starting photobooth
    session_id = f"SES-{uuid.uuid4().hex[:8].upper()}"
    return {
        "session_id": session_id,
        "allowed": True,
        "session_status": "ready_to_shoot",
        "order_id": order_id
    }

if __name__ == "__main__":
    print("Starting Mock Payment Server...")
    print("Swagger docs available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
