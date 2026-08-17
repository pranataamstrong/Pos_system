from dotenv import load_dotenv
from pathlib import Path
import os

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, BeforeValidator, ConfigDict
from typing import List, Optional, Annotated, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from collections import defaultdict
import logging
import bcrypt
import jwt
import uuid
import base64
import asyncio
from escpos.printer import Dummy, Network

# ---------------- DB ----------------
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_ALGORITHM = "HS256"

def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]

# ---------------- Helpers ----------------
PyObjectId = Annotated[str, BeforeValidator(str)]

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)

# ---------------- Models ----------------
class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = "cashier"

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class CategoryInput(BaseModel):
    name: str
    color: str = "#4338CA"

class ProductInput(BaseModel):
    name: str
    category_id: Optional[str] = None
    price: float
    cost: float = 0.0
    stock: int = 0
    sku: Optional[str] = None
    barcode: Optional[str] = None
    image: Optional[str] = None

class SettingsInput(BaseModel):
    store_name: str = "Mandiri POS"
    address: str = ""
    phone: str = ""
    logo: Optional[str] = None
    footer: str = "Terima kasih atas kunjungan Anda"
    low_stock_threshold: int = 10
    point_value: float = 100
    enable_shift_print: bool = True
    printer_ip: str = ""
    printer_port: int = 9100

class CartItem(BaseModel):
    product_id: str
    name: str
    price: float
    cost: float = 0.0
    qty: int

class CheckoutInput(BaseModel):
    items: List[CartItem]
    discount: float = 0.0
    discount_type: str = "amount"  # amount | percent
    discount_value: float = 0.0
    payment_method: str  # cash | card | qris
    amount_paid: float = 0.0
    customer_id: Optional[str] = None
    points_redeemed: int = 0
    note: Optional[str] = None

class CustomerInput(BaseModel):
    name: str
    phone: str = ""
    email: Optional[str] = None

class ShiftOpenInput(BaseModel):
    opening_cash: float = 0.0

class ShiftCloseInput(BaseModel):
    counted_cash: float = 0.0
    note: Optional[str] = None

class PrintNetworkInput(BaseModel):
    ip: Optional[str] = None
    port: Optional[int] = None

# ---------------- Auth dependency ----------------
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Tidak terautentikasi")
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token kadaluarsa")
    except Exception:
        raise HTTPException(status_code=401, detail="Token tidak valid")
    if not user:
        raise HTTPException(status_code=401, detail="User tidak ditemukan")
    user["id"] = str(user.pop("_id"))
    user.pop("password_hash", None)
    return user

async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Akses khusus admin")
    return user

def serialize(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc

# ---------------- App ----------------
app = FastAPI()
api_router = APIRouter(prefix="/api")

@api_router.get("/")
async def root():
    return {"message": "Mandiri POS API"}

# ------ Auth routes ------
@api_router.post("/auth/register")
async def register(data: RegisterInput, admin: dict = Depends(require_admin)):
    email = data.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    doc = {"email": email, "password_hash": hash_password(data.password),
           "name": data.name, "role": data.role, "created_at": now_iso()}
    res = await db.users.insert_one(doc)
    doc["_id"] = res.inserted_id
    u = serialize(doc); u.pop("password_hash", None)
    return u

@api_router.post("/auth/login")
async def login(data: LoginInput):
    email = data.email.lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau kata sandi salah")
    token = create_access_token(str(user["_id"]), email)
    u = serialize(user); u.pop("password_hash", None)
    return {"token": token, "user": u}

@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

@api_router.get("/users")
async def list_users(admin: dict = Depends(require_admin)):
    users = await db.users.find().sort("created_at", -1).to_list(500)
    out = []
    for u in users:
        u = serialize(u); u.pop("password_hash", None)
        out.append(u)
    return out

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Tidak dapat menghapus akun sendiri")
    await db.users.delete_one({"_id": ObjectId(user_id)})
    return {"ok": True}

# ------ Categories ------
@api_router.get("/categories")
async def list_categories(user: dict = Depends(get_current_user)):
    cats = await db.categories.find().sort("name", 1).to_list(500)
    return [serialize(c) for c in cats]

@api_router.post("/categories")
async def create_category(data: CategoryInput, admin: dict = Depends(require_admin)):
    doc = {"name": data.name, "color": data.color, "created_at": now_iso()}
    res = await db.categories.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)

@api_router.put("/categories/{cat_id}")
async def update_category(cat_id: str, data: CategoryInput, admin: dict = Depends(require_admin)):
    await db.categories.update_one({"_id": ObjectId(cat_id)}, {"$set": {"name": data.name, "color": data.color}})
    doc = await db.categories.find_one({"_id": ObjectId(cat_id)})
    return serialize(doc)

@api_router.delete("/categories/{cat_id}")
async def delete_category(cat_id: str, admin: dict = Depends(require_admin)):
    await db.categories.delete_one({"_id": ObjectId(cat_id)})
    await db.products.update_many({"category_id": cat_id}, {"$set": {"category_id": None}})
    return {"ok": True}

# ------ Products ------
@api_router.get("/products")
async def list_products(user: dict = Depends(get_current_user)):
    prods = await db.products.find().sort("name", 1).to_list(1000)
    return [serialize(p) for p in prods]

@api_router.post("/products")
async def create_product(data: ProductInput, admin: dict = Depends(require_admin)):
    doc = data.model_dump()
    doc["created_at"] = now_iso()
    res = await db.products.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)

@api_router.put("/products/{prod_id}")
async def update_product(prod_id: str, data: ProductInput, admin: dict = Depends(require_admin)):
    await db.products.update_one({"_id": ObjectId(prod_id)}, {"$set": data.model_dump()})
    doc = await db.products.find_one({"_id": ObjectId(prod_id)})
    return serialize(doc)

@api_router.delete("/products/{prod_id}")
async def delete_product(prod_id: str, admin: dict = Depends(require_admin)):
    await db.products.delete_one({"_id": ObjectId(prod_id)})
    return {"ok": True}

# ------ Checkout / Sales ------
@api_router.post("/sales")
async def checkout(data: CheckoutInput, user: dict = Depends(get_current_user)):
    if not data.items:
        raise HTTPException(status_code=400, detail="Keranjang kosong")
    # validate stock availability (aggregate qty per product)
    qty_by_product = defaultdict(int)
    for i in data.items:
        qty_by_product[i.product_id] += i.qty
    for pid, qty in qty_by_product.items():
        try:
            prod = await db.products.find_one({"_id": ObjectId(pid)})
        except Exception:
            prod = None
        if prod is not None and qty > prod.get("stock", 0):
            raise HTTPException(status_code=400, detail=f"Stok '{prod.get('name', '')}' tidak mencukupi (sisa {prod.get('stock', 0)})")
    subtotal = sum(i.price * i.qty for i in data.items)
    total_cost = sum(i.cost * i.qty for i in data.items)
    # loyalty: resolve customer, validate & compute redemption
    settings = await db.settings.find_one({"key": "store"})
    point_value = settings.get("point_value", 100) if settings else 100
    cust = None
    if data.customer_id:
        try:
            cust = await db.customers.find_one({"_id": ObjectId(data.customer_id)})
        except Exception:
            cust = None
    points_redeemed = max(0, int(data.points_redeemed or 0))
    if points_redeemed > 0:
        if not cust:
            raise HTTPException(status_code=400, detail="Pilih pelanggan dulu untuk tukar poin")
        if points_redeemed > cust.get("points", 0):
            raise HTTPException(status_code=400, detail=f"Poin tidak mencukupi (tersedia {cust.get('points', 0)})")
    redeem_value = points_redeemed * point_value
    total = max(0.0, subtotal - data.discount - redeem_value)
    profit = total - total_cost
    change = max(0.0, data.amount_paid - total) if data.payment_method == "cash" else 0.0
    receipt_no = "INV-" + datetime.now(timezone.utc).strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
    # active shift for this cashier
    shift = await db.shifts.find_one({"cashier_id": user["id"], "status": "open"})
    shift_id = str(shift["_id"]) if shift else None
    customer_name = cust.get("name") if cust else None
    points_earned = int(total // 1000) if cust else 0
    doc = {
        "receipt_no": receipt_no,
        "cashier_id": user["id"], "cashier_name": user.get("name", ""),
        "items": [i.model_dump() for i in data.items],
        "subtotal": subtotal, "discount": data.discount,
        "discount_type": data.discount_type, "discount_value": data.discount_value,
        "points_redeemed": points_redeemed, "redeem_value": redeem_value,
        "total": total, "total_cost": total_cost, "profit": profit,
        "payment_method": data.payment_method, "amount_paid": data.amount_paid,
        "change": change, "note": data.note,
        "shift_id": shift_id,
        "customer_id": data.customer_id, "customer_name": customer_name,
        "points_earned": points_earned,
        "created_at": now_iso(),
    }
    res = await db.sales.insert_one(doc)
    doc["_id"] = res.inserted_id
    # reduce stock
    for i in data.items:
        try:
            await db.products.update_one({"_id": ObjectId(i.product_id)}, {"$inc": {"stock": -i.qty}})
        except Exception:
            pass
    # update loyalty points (earn - redeem) and spend
    if cust:
        net_points = points_earned - points_redeemed
        try:
            await db.customers.update_one({"_id": ObjectId(data.customer_id)},
                                          {"$inc": {"points": net_points, "total_spent": total}})
        except Exception:
            pass
    return serialize(doc)

@api_router.get("/sales")
async def list_sales(user: dict = Depends(get_current_user), limit: int = 200):
    sales = await db.sales.find().sort("created_at", -1).to_list(limit)
    return [serialize(s) for s in sales]

# ------ Settings ------
@api_router.get("/settings")
async def get_settings(user: dict = Depends(get_current_user)):
    defaults = SettingsInput().model_dump()
    doc = await db.settings.find_one({"key": "store"})
    if not doc:
        return defaults
    doc.pop("_id", None)
    doc.pop("key", None)
    return {**defaults, **doc}

@api_router.put("/settings")
async def update_settings(data: SettingsInput, admin: dict = Depends(require_admin)):
    await db.settings.update_one({"key": "store"}, {"$set": {**data.model_dump(), "key": "store"}}, upsert=True)
    return data.model_dump()

# ------ Thermal Printing (ESC/POS, 80mm) ------
def _rp(n) -> str:
    return "Rp " + f"{int(round(n or 0)):,}".replace(",", ".")

def build_receipt_bytes(sale: dict, store: dict) -> bytes:
    """Generate ESC/POS command bytes for an 80mm (48 col) thermal receipt."""
    d = Dummy()
    W = 48
    method_label = {"cash": "Tunai", "card": "Kartu", "qris": "QRIS"}

    def two(left, right):
        left, right = str(left), str(right)
        if len(left) + len(right) >= W:
            left = left[: max(0, W - len(right) - 1)]
        return left + " " * (W - len(left) - len(right)) + right + "\n"

    d.set(align="center", bold=True, double_width=True, double_height=True)
    d.text((store.get("store_name") or "Mandiri POS") + "\n")
    d.set(align="center", bold=False, double_width=False, double_height=False)
    if store.get("address"):
        d.text(str(store["address"]) + "\n")
    if store.get("phone"):
        d.text(str(store["phone"]) + "\n")
    d.text("-" * W + "\n")
    d.set(align="left")
    dt = str(sale.get("created_at", ""))[:19].replace("T", " ")
    d.text(two(sale.get("receipt_no", ""), dt))
    d.text("Kasir: " + str(sale.get("cashier_name", "")) + "\n")
    if sale.get("customer_name"):
        d.text("Pelanggan: " + str(sale["customer_name"]) + "\n")
    d.text("-" * W + "\n")
    for it in sale.get("items", []):
        d.text(str(it.get("name", "")) + "\n")
        d.text(two(f"  {it.get('qty', 0)} x {_rp(it.get('price', 0))}", _rp(it.get("price", 0) * it.get("qty", 0))))
    d.text("-" * W + "\n")
    d.text(two("Subtotal", _rp(sale.get("subtotal", 0))))
    if sale.get("discount", 0) > 0:
        d.text(two("Diskon", "-" + _rp(sale["discount"])))
    if sale.get("redeem_value", 0) > 0:
        d.text(two(f"Tukar Poin ({sale.get('points_redeemed', 0)})", "-" + _rp(sale["redeem_value"])))
    d.set(bold=True)
    d.text(two("TOTAL", _rp(sale.get("total", 0))))
    d.set(bold=False)
    pm = method_label.get(sale.get("payment_method"), str(sale.get("payment_method", "")))
    d.text(two(f"Bayar ({pm})", _rp(sale.get("amount_paid") or sale.get("total", 0))))
    if sale.get("payment_method") == "cash":
        d.text(two("Kembalian", _rp(sale.get("change", 0))))
    if sale.get("points_earned", 0) > 0:
        d.text(f"Poin diperoleh: +{sale['points_earned']}\n")
    d.text("-" * W + "\n")
    d.set(align="center")
    d.text((store.get("footer") or "Terima kasih atas kunjungan Anda") + "\n\n")
    try:
        d.cut()
    except Exception:
        d.text("\n\n\n")
    return d.output

async def _get_sale_and_store(sale_id: str):
    try:
        sale = await db.sales.find_one({"_id": ObjectId(sale_id)})
    except Exception:
        sale = None
    if not sale:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    settings = await db.settings.find_one({"key": "store"}) or {}
    return serialize(sale), settings

@api_router.get("/print/{sale_id}")
async def print_receipt_bytes(sale_id: str, user: dict = Depends(get_current_user)):
    """Return base64-encoded ESC/POS bytes (for Web Bluetooth printing from the browser)."""
    sale, settings = await _get_sale_and_store(sale_id)
    raw = build_receipt_bytes(sale, settings)
    return {"data": base64.b64encode(raw).decode("ascii")}

def _send_to_network_printer(ip: str, port: int, raw: bytes):
    p = Network(ip, port=port, timeout=8)
    p._raw(raw)
    p.close()

@api_router.post("/print/{sale_id}/network")
async def print_receipt_network(sale_id: str, body: PrintNetworkInput, user: dict = Depends(get_current_user)):
    sale, settings = await _get_sale_and_store(sale_id)
    ip = body.ip or settings.get("printer_ip")
    port = int(body.port or settings.get("printer_port") or 9100)
    if not ip:
        raise HTTPException(status_code=400, detail="IP printer belum diatur. Isi di Pengaturan.")
    raw = build_receipt_bytes(sale, settings)
    try:
        await asyncio.to_thread(_send_to_network_printer, ip, port, raw)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal terhubung ke printer {ip}:{port}. {str(e)[:120]}")
    return {"ok": True, "message": f"Struk dikirim ke {ip}:{port}"}

# ------ Notifications (low stock, in-app) ------
@api_router.get("/notifications")
async def get_notifications(user: dict = Depends(get_current_user)):
    settings = await db.settings.find_one({"key": "store"})
    threshold = settings.get("low_stock_threshold", 10) if settings else 10
    prods = await db.products.find({"stock": {"$lte": threshold}}).sort("stock", 1).to_list(200)
    items = [{"id": str(p["_id"]), "name": p["name"], "stock": p.get("stock", 0)} for p in prods]
    return {"threshold": threshold, "count": len(items), "items": items}

# ------ Customers ------
@api_router.get("/customers")
async def list_customers(user: dict = Depends(get_current_user)):
    custs = await db.customers.find().sort("name", 1).to_list(2000)
    return [serialize(c) for c in custs]

@api_router.post("/customers")
async def create_customer(data: CustomerInput, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc.update({"points": 0, "total_spent": 0.0, "created_at": now_iso()})
    res = await db.customers.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)

@api_router.put("/customers/{cust_id}")
async def update_customer(cust_id: str, data: CustomerInput, admin: dict = Depends(require_admin)):
    await db.customers.update_one({"_id": ObjectId(cust_id)}, {"$set": data.model_dump()})
    doc = await db.customers.find_one({"_id": ObjectId(cust_id)})
    return serialize(doc)

@api_router.delete("/customers/{cust_id}")
async def delete_customer(cust_id: str, admin: dict = Depends(require_admin)):
    await db.customers.delete_one({"_id": ObjectId(cust_id)})
    return {"ok": True}

# ------ Shifts (buka/tutup kas) ------
@api_router.get("/shifts/current")
async def current_shift(user: dict = Depends(get_current_user)):
    shift = await db.shifts.find_one({"cashier_id": user["id"], "status": "open"})
    return serialize(shift) if shift else None

@api_router.post("/shifts/open")
async def open_shift(data: ShiftOpenInput, user: dict = Depends(get_current_user)):
    existing = await db.shifts.find_one({"cashier_id": user["id"], "status": "open"})
    if existing:
        raise HTTPException(status_code=400, detail="Shift sudah dibuka")
    doc = {
        "cashier_id": user["id"], "cashier_name": user.get("name", ""),
        "opening_cash": data.opening_cash, "status": "open",
        "opened_at": now_iso(), "closed_at": None,
    }
    res = await db.shifts.insert_one(doc)
    doc["_id"] = res.inserted_id
    return serialize(doc)

@api_router.post("/shifts/close")
async def close_shift(data: ShiftCloseInput, user: dict = Depends(get_current_user)):
    shift = await db.shifts.find_one({"cashier_id": user["id"], "status": "open"})
    if not shift:
        raise HTTPException(status_code=400, detail="Tidak ada shift aktif")
    shift_id = str(shift["_id"])
    sales = await db.sales.find({"shift_id": shift_id}).to_list(10000)
    cash_sales = sum(s["total"] for s in sales if s.get("payment_method") == "cash")
    total_sales = sum(s["total"] for s in sales)
    expected_cash = shift.get("opening_cash", 0) + cash_sales
    difference = data.counted_cash - expected_cash
    await db.shifts.update_one({"_id": shift["_id"]}, {"$set": {
        "status": "closed", "closed_at": now_iso(),
        "counted_cash": data.counted_cash, "expected_cash": expected_cash,
        "cash_sales": cash_sales, "total_sales": total_sales,
        "transactions": len(sales), "difference": difference, "note": data.note,
    }})
    shift = await db.shifts.find_one({"_id": shift["_id"]})
    return serialize(shift)

@api_router.get("/shifts")
async def list_shifts(user: dict = Depends(get_current_user), limit: int = 100):
    q = {} if user.get("role") == "admin" else {"cashier_id": user["id"]}
    shifts = await db.shifts.find(q).sort("opened_at", -1).to_list(limit)
    return [serialize(s) for s in shifts]

@api_router.get("/sales/{sale_id}")
async def get_sale(sale_id: str, user: dict = Depends(get_current_user)):
    s = await db.sales.find_one({"_id": ObjectId(sale_id)})
    if not s:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    return serialize(s)

# ------ Reports ------
def _parse_range(start: Optional[str], end: Optional[str]):
    return start, end

async def _fetch_sales(start: Optional[str], end: Optional[str]):
    q: dict = {}
    if start or end:
        q["created_at"] = {}
        if start:
            q["created_at"]["$gte"] = start
        if end:
            q["created_at"]["$lte"] = end + "T23:59:59.999999+00:00"
    sales = await db.sales.find(q).to_list(10000)
    return sales

@api_router.get("/reports/summary")
async def report_summary(user: dict = Depends(get_current_user), start: Optional[str] = None, end: Optional[str] = None):
    sales = await _fetch_sales(start, end)
    total_sales = sum(s["total"] for s in sales)
    total_profit = sum(s.get("profit", 0) for s in sales)
    count = len(sales)
    items_sold = sum(sum(it["qty"] for it in s["items"]) for s in sales)
    avg = total_sales / count if count else 0
    return {"total_sales": total_sales, "total_profit": total_profit,
            "transactions": count, "items_sold": items_sold, "avg_transaction": avg}

@api_router.get("/reports/sales-over-time")
async def report_sales_over_time(user: dict = Depends(get_current_user), start: Optional[str] = None, end: Optional[str] = None):
    sales = await _fetch_sales(start, end)
    by_day: dict = defaultdict(lambda: {"total": 0.0, "profit": 0.0, "count": 0})
    for s in sales:
        day = s["created_at"][:10]
        by_day[day]["total"] += s["total"]
        by_day[day]["profit"] += s.get("profit", 0)
        by_day[day]["count"] += 1
    out = [{"date": d, **v} for d, v in sorted(by_day.items())]
    return out

@api_router.get("/reports/top-products")
async def report_top_products(user: dict = Depends(get_current_user), start: Optional[str] = None, end: Optional[str] = None):
    sales = await _fetch_sales(start, end)
    agg: dict = defaultdict(lambda: {"qty": 0, "revenue": 0.0})
    for s in sales:
        for it in s["items"]:
            agg[it["name"]]["qty"] += it["qty"]
            agg[it["name"]]["revenue"] += it["price"] * it["qty"]
    out = [{"name": n, **v} for n, v in agg.items()]
    out.sort(key=lambda x: x["revenue"], reverse=True)
    return out[:10]

@api_router.get("/reports/by-category")
async def report_by_category(user: dict = Depends(get_current_user), start: Optional[str] = None, end: Optional[str] = None):
    sales = await _fetch_sales(start, end)
    products = await db.products.find().to_list(2000)
    prod_cat = {str(p["_id"]): p.get("category_id") for p in products}
    cats = await db.categories.find().to_list(500)
    cat_name = {str(c["_id"]): c["name"] for c in cats}
    agg: dict = defaultdict(float)
    for s in sales:
        for it in s["items"]:
            cid = prod_cat.get(it["product_id"])
            name = cat_name.get(cid, "Tanpa Kategori") if cid else "Tanpa Kategori"
            agg[name] += it["price"] * it["qty"]
    return [{"name": n, "value": v} for n, v in sorted(agg.items(), key=lambda x: x[1], reverse=True)]

@api_router.get("/reports/payment-methods")
async def report_payment_methods(user: dict = Depends(get_current_user), start: Optional[str] = None, end: Optional[str] = None):
    sales = await _fetch_sales(start, end)
    agg: dict = defaultdict(lambda: {"total": 0.0, "count": 0})
    for s in sales:
        agg[s["payment_method"]]["total"] += s["total"]
        agg[s["payment_method"]]["count"] += 1
    labels = {"cash": "Tunai", "card": "Kartu", "qris": "QRIS"}
    return [{"method": labels.get(m, m), "key": m, **v} for m, v in agg.items()]

@api_router.get("/reports/low-stock")
async def report_low_stock(user: dict = Depends(get_current_user), threshold: int = 10):
    prods = await db.products.find({"stock": {"$lte": threshold}}).sort("stock", 1).to_list(200)
    return [serialize(p) for p in prods]

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com").lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({"email": admin_email, "password_hash": hash_password(admin_password),
                                   "name": "Owner", "role": "admin", "created_at": now_iso()})
        logger.info("Admin seeded")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
    await seed_demo()

DEMO_IMAGES = {
    "Kopi Susu": "https://images.unsplash.com/photo-1637419226404-aab6130b2a61?crop=entropy&cs=srgb&fm=jpg&w=600&q=80",
    "Americano": "https://images.unsplash.com/photo-1612880202987-b1ec29fb0839?crop=entropy&cs=srgb&fm=jpg&w=600&q=80",
    "Croissant": "https://images.pexels.com/photos/34773646/pexels-photo-34773646.jpeg?auto=compress&cs=tinysrgb&w=600",
    "Cream Puff": "https://images.pexels.com/photos/9395559/pexels-photo-9395559.jpeg?auto=compress&cs=tinysrgb&w=600",
}

async def seed_demo():
    if await db.products.count_documents({}) > 0:
        return
    cat_defs = [("Minuman", "#4338CA"), ("Makanan", "#10B981"), ("Snack", "#F59E0B")]
    cat_ids = {}
    for name, color in cat_defs:
        res = await db.categories.insert_one({"name": name, "color": color, "created_at": now_iso()})
        cat_ids[name] = str(res.inserted_id)
    prods = [
        ("Kopi Susu", "Minuman", 18000, 8000, 50),
        ("Americano", "Minuman", 15000, 6000, 50),
        ("Teh Manis", "Minuman", 8000, 3000, 80),
        ("Air Mineral", "Minuman", 5000, 2000, 100),
        ("Croissant", "Makanan", 22000, 10000, 30),
        ("Nasi Goreng", "Makanan", 28000, 14000, 25),
        ("Mie Ayam", "Makanan", 25000, 12000, 25),
        ("Cream Puff", "Snack", 12000, 5000, 40),
        ("Kentang Goreng", "Snack", 15000, 6000, 35),
        ("Roti Bakar", "Snack", 14000, 6000, 30),
    ]
    for name, cat, price, cost, stock in prods:
        await db.products.insert_one({
            "name": name, "category_id": cat_ids[cat], "price": price, "cost": cost,
            "stock": stock, "sku": None, "image": DEMO_IMAGES.get(name), "created_at": now_iso(),
        })
    logger.info("Demo data seeded")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
