"""Backend API tests for Mandiri POS."""
import os
import time
import pytest
import requests

BASE = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE:
    # fallback to reading frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE = line.strip().split("=", 1)[1].strip('"')
BASE = BASE.rstrip("/")
API = f"{BASE}/api"

ADMIN_EMAIL = "pranataamstrong@gmail.com"
ADMIN_PASS = "admin123"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and "user" in data
    assert data["user"]["role"] == "admin"
    return data["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------------- Auth ----------------
class TestAuth:
    def test_login_success(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS})
        assert r.status_code == 200
        assert r.json()["user"]["email"] == ADMIN_EMAIL

    def test_login_wrong_password(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_with_token(self, admin_headers):
        r = requests.get(f"{API}/auth/me", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL


# ---------------- Categories CRUD ----------------
class TestCategories:
    created_id = None

    def test_list(self, admin_headers):
        r = requests.get(f"{API}/categories", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_update_delete(self, admin_headers):
        r = requests.post(f"{API}/categories", headers=admin_headers,
                          json={"name": "TEST_Cat", "color": "#123456"})
        assert r.status_code == 200
        cid = r.json()["id"]
        assert r.json()["name"] == "TEST_Cat"

        r = requests.put(f"{API}/categories/{cid}", headers=admin_headers,
                         json={"name": "TEST_Cat2", "color": "#654321"})
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Cat2"

        r = requests.delete(f"{API}/categories/{cid}", headers=admin_headers)
        assert r.status_code == 200


# ---------------- Products CRUD ----------------
class TestProducts:
    def test_list(self, admin_headers):
        r = requests.get(f"{API}/products", headers=admin_headers)
        assert r.status_code == 200
        products = r.json()
        assert len(products) >= 10  # seeded

    def test_crud(self, admin_headers):
        r = requests.post(f"{API}/products", headers=admin_headers,
                          json={"name": "TEST_Prod", "price": 10000, "cost": 5000, "stock": 20})
        assert r.status_code == 200
        pid = r.json()["id"]
        assert r.json()["price"] == 10000

        # verify via GET list
        r2 = requests.get(f"{API}/products", headers=admin_headers)
        assert any(p["id"] == pid for p in r2.json())

        r = requests.put(f"{API}/products/{pid}", headers=admin_headers,
                         json={"name": "TEST_Prod2", "price": 12000, "cost": 5000, "stock": 15})
        assert r.status_code == 200
        assert r.json()["price"] == 12000

        r = requests.delete(f"{API}/products/{pid}", headers=admin_headers)
        assert r.status_code == 200

    def test_create_requires_admin(self):
        r = requests.post(f"{API}/products", json={"name": "x", "price": 1})
        assert r.status_code == 401


# ---------------- Sales / Checkout ----------------
class TestSales:
    def test_checkout_reduces_stock_and_computes(self, admin_headers):
        # Get a product
        prods = requests.get(f"{API}/products", headers=admin_headers).json()
        p = prods[0]
        initial_stock = p["stock"]

        payload = {
            "items": [{"product_id": p["id"], "name": p["name"],
                       "price": p["price"], "cost": p["cost"], "qty": 2}],
            "discount": 1000,
            "payment_method": "cash",
            "amount_paid": p["price"] * 2 + 5000,
        }
        r = requests.post(f"{API}/sales", headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        sale = r.json()
        assert sale["subtotal"] == p["price"] * 2
        assert sale["total"] == p["price"] * 2 - 1000
        assert sale["profit"] == sale["total"] - p["cost"] * 2
        assert sale["change"] == payload["amount_paid"] - sale["total"]
        assert sale["receipt_no"].startswith("INV-")

        # stock reduced
        r2 = requests.get(f"{API}/products", headers=admin_headers)
        new_p = next(x for x in r2.json() if x["id"] == p["id"])
        assert new_p["stock"] == initial_stock - 2

        # can fetch sale
        r3 = requests.get(f"{API}/sales/{sale['id']}", headers=admin_headers)
        assert r3.status_code == 200

    def test_empty_cart_rejected(self, admin_headers):
        r = requests.post(f"{API}/sales", headers=admin_headers,
                         json={"items": [], "payment_method": "cash"})
        assert r.status_code == 400

    def test_list_sales(self, admin_headers):
        r = requests.get(f"{API}/sales", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------- Reports ----------------
class TestReports:
    def test_summary(self, admin_headers):
        r = requests.get(f"{API}/reports/summary", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        for k in ("total_sales", "total_profit", "transactions", "items_sold", "avg_transaction"):
            assert k in d

    def test_sales_over_time(self, admin_headers):
        r = requests.get(f"{API}/reports/sales-over-time", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_top_products(self, admin_headers):
        r = requests.get(f"{API}/reports/top-products", headers=admin_headers)
        assert r.status_code == 200

    def test_by_category(self, admin_headers):
        r = requests.get(f"{API}/reports/by-category", headers=admin_headers)
        assert r.status_code == 200

    def test_payment_methods(self, admin_headers):
        r = requests.get(f"{API}/reports/payment-methods", headers=admin_headers)
        assert r.status_code == 200

    def test_low_stock(self, admin_headers):
        r = requests.get(f"{API}/reports/low-stock?threshold=10", headers=admin_headers)
        assert r.status_code == 200


# ---------------- User management + Role gating ----------------
class TestUsers:
    def test_create_cashier_and_login_and_role_restriction(self, admin_headers):
        email = f"test_cashier_{int(time.time())}@example.com"
        r = requests.post(f"{API}/auth/register", headers=admin_headers,
                          json={"email": email, "password": "pass1234",
                                "name": "Test Cashier", "role": "cashier"})
        assert r.status_code == 200, r.text
        uid = r.json()["id"]

        # cashier can log in
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "pass1234"})
        assert r.status_code == 200
        cashier_token = r.json()["token"]
        ch = {"Authorization": f"Bearer {cashier_token}"}

        # cashier cannot list users
        r = requests.get(f"{API}/users", headers=ch)
        assert r.status_code == 403

        # cashier cannot create product
        r = requests.post(f"{API}/products", headers=ch, json={"name": "x", "price": 1})
        assert r.status_code == 403

        # cashier can list products
        r = requests.get(f"{API}/products", headers=ch)
        assert r.status_code == 200

        # cleanup
        r = requests.delete(f"{API}/users/{uid}", headers=admin_headers)
        assert r.status_code == 200

    def test_list_users(self, admin_headers):
        r = requests.get(f"{API}/users", headers=admin_headers)
        assert r.status_code == 200
        assert any(u["email"] == ADMIN_EMAIL for u in r.json())


# ---------------- Settings (new) ----------------
class TestSettings:
    def test_get_settings_default_or_saved(self, admin_headers):
        r = requests.get(f"{API}/settings", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        for k in ("store_name", "address", "phone", "footer"):
            assert k in d

    def test_put_settings_admin_and_persisted(self, admin_headers):
        payload = {
            "store_name": "TEST Toko Kopi",
            "address": "Jl. Testing No. 1",
            "phone": "0812-3456",
            "logo": "https://example.com/logo.png",
            "footer": "TEST footer",
        }
        r = requests.put(f"{API}/settings", headers=admin_headers, json=payload)
        assert r.status_code == 200
        # verify persisted
        r2 = requests.get(f"{API}/settings", headers=admin_headers)
        d = r2.json()
        assert d["store_name"] == payload["store_name"]
        assert d["address"] == payload["address"]
        assert d["footer"] == payload["footer"]

    def test_put_settings_forbidden_for_cashier(self, admin_headers):
        email = f"test_settings_cashier_{int(time.time())}@example.com"
        r = requests.post(f"{API}/auth/register", headers=admin_headers,
                          json={"email": email, "password": "pass1234", "name": "SC", "role": "cashier"})
        uid = r.json()["id"]
        tok = requests.post(f"{API}/auth/login", json={"email": email, "password": "pass1234"}).json()["token"]
        ch = {"Authorization": f"Bearer {tok}"}
        r = requests.put(f"{API}/settings", headers=ch, json={"store_name": "hack"})
        assert r.status_code == 403
        # cashier can GET
        r = requests.get(f"{API}/settings", headers=ch)
        assert r.status_code == 200
        requests.delete(f"{API}/users/{uid}", headers=admin_headers)


# ---------------- Stock guard (new) ----------------
class TestStockGuard:
    def test_oversell_returns_400(self, admin_headers):
        # create product with stock=2
        r = requests.post(f"{API}/products", headers=admin_headers,
                          json={"name": "TEST_StockGuard", "price": 1000, "cost": 500, "stock": 2})
        assert r.status_code == 200
        p = r.json()
        payload = {
            "items": [{"product_id": p["id"], "name": p["name"], "price": p["price"], "cost": p["cost"], "qty": 5}],
            "payment_method": "cash",
            "amount_paid": 5000,
        }
        r = requests.post(f"{API}/sales", headers=admin_headers, json=payload)
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "tidak mencukupi" in detail.lower() or "stok" in detail.lower()
        # verify stock NOT decremented
        prods = requests.get(f"{API}/products", headers=admin_headers).json()
        cur = next(x for x in prods if x["id"] == p["id"])
        assert cur["stock"] == 2
        requests.delete(f"{API}/products/{p['id']}", headers=admin_headers)

    def test_product_with_barcode_persisted(self, admin_headers):
        r = requests.post(f"{API}/products", headers=admin_headers,
                          json={"name": "TEST_Barcode", "price": 1000, "stock": 5, "barcode": "TESTBC123"})
        assert r.status_code == 200
        pid = r.json()["id"]
        assert r.json().get("barcode") == "TESTBC123"
        # verify in list
        prods = requests.get(f"{API}/products", headers=admin_headers).json()
        p = next(x for x in prods if x["id"] == pid)
        assert p.get("barcode") == "TESTBC123"
        requests.delete(f"{API}/products/{pid}", headers=admin_headers)
