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


# ---------------- Notifications (iteration 3) ----------------
class TestNotifications:
    def test_shape_and_threshold_effect(self, admin_headers):
        r = requests.get(f"{API}/notifications", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        for k in ("threshold", "count", "items"):
            assert k in d
        assert isinstance(d["items"], list)
        assert d["count"] == len(d["items"])
        # set threshold very high via settings and expect items > 0
        s = requests.get(f"{API}/settings", headers=admin_headers).json()
        s["low_stock_threshold"] = 9999
        r = requests.put(f"{API}/settings", headers=admin_headers, json=s)
        assert r.status_code == 200
        r = requests.get(f"{API}/notifications", headers=admin_headers)
        d = r.json()
        assert d["threshold"] == 9999
        assert d["count"] > 0
        # restore
        s["low_stock_threshold"] = 10
        requests.put(f"{API}/settings", headers=admin_headers, json=s)


# ---------------- Customers CRUD + role restrictions ----------------
class TestCustomers:
    def test_crud_admin(self, admin_headers):
        r = requests.post(f"{API}/customers", headers=admin_headers,
                          json={"name": "TEST_Cust", "phone": "0812", "email": None})
        assert r.status_code == 200
        c = r.json()
        assert c["name"] == "TEST_Cust"
        assert c["points"] == 0
        cid = c["id"]
        # get list
        r2 = requests.get(f"{API}/customers", headers=admin_headers)
        assert any(x["id"] == cid for x in r2.json())
        # update
        r = requests.put(f"{API}/customers/{cid}", headers=admin_headers,
                        json={"name": "TEST_Cust2", "phone": "0813"})
        assert r.status_code == 200
        assert r.json()["name"] == "TEST_Cust2"
        # delete
        r = requests.delete(f"{API}/customers/{cid}", headers=admin_headers)
        assert r.status_code == 200

    def test_cashier_can_list_and_create_but_not_edit_delete(self, admin_headers):
        email = f"test_cashier_cust_{int(time.time())}@example.com"
        r = requests.post(f"{API}/auth/register", headers=admin_headers,
                          json={"email": email, "password": "pass1234", "name": "CC", "role": "cashier"})
        uid = r.json()["id"]
        tok = requests.post(f"{API}/auth/login", json={"email": email, "password": "pass1234"}).json()["token"]
        ch = {"Authorization": f"Bearer {tok}"}
        # list ok
        assert requests.get(f"{API}/customers", headers=ch).status_code == 200
        # create ok
        r = requests.post(f"{API}/customers", headers=ch, json={"name": "TEST_C2", "phone": ""})
        assert r.status_code == 200
        cid = r.json()["id"]
        # edit forbidden
        r = requests.put(f"{API}/customers/{cid}", headers=ch, json={"name": "X", "phone": ""})
        assert r.status_code == 403
        # delete forbidden
        r = requests.delete(f"{API}/customers/{cid}", headers=ch)
        assert r.status_code == 403
        # cleanup by admin
        requests.delete(f"{API}/customers/{cid}", headers=admin_headers)
        requests.delete(f"{API}/users/{uid}", headers=admin_headers)


# ---------------- Percent discount + Points on checkout ----------------
class TestDiscountAndPoints:
    def test_percent_discount_and_points(self, admin_headers):
        # create product with predictable price
        r = requests.post(f"{API}/products", headers=admin_headers,
                          json={"name": "TEST_DiscProd", "price": 10000, "cost": 4000, "stock": 20})
        p = r.json()
        # create customer
        r = requests.post(f"{API}/customers", headers=admin_headers,
                          json={"name": "TEST_LoyalCust", "phone": ""})
        cust = r.json()
        cid = cust["id"]
        # checkout: 1 * 10000, percent 10 -> discount 1000, total 9000
        payload = {
            "items": [{"product_id": p["id"], "name": p["name"], "price": 10000, "cost": 4000, "qty": 1}],
            "discount": 1000,
            "discount_type": "percent",
            "discount_value": 10,
            "payment_method": "cash",
            "amount_paid": 10000,
            "customer_id": cid,
        }
        r = requests.post(f"{API}/sales", headers=admin_headers, json=payload)
        assert r.status_code == 200, r.text
        sale = r.json()
        assert sale["subtotal"] == 10000
        assert sale["total"] == 9000
        assert sale["discount_type"] == "percent"
        assert sale["discount_value"] == 10
        assert sale["customer_name"] == "TEST_LoyalCust"
        assert sale["points_earned"] == 9  # floor(9000/1000)
        # customer points updated
        cust2 = next(c for c in requests.get(f"{API}/customers", headers=admin_headers).json() if c["id"] == cid)
        assert cust2["points"] == 9
        assert cust2["total_spent"] == 9000
        # cleanup
        requests.delete(f"{API}/customers/{cid}", headers=admin_headers)
        requests.delete(f"{API}/products/{p['id']}", headers=admin_headers)


# ---------------- Shifts open/close ----------------
class TestShifts:
    def test_full_shift_cycle(self, admin_headers):
        # create dedicated cashier so we don't collide with admin's shift
        email = f"test_shift_cashier_{int(time.time())}@example.com"
        r = requests.post(f"{API}/auth/register", headers=admin_headers,
                          json={"email": email, "password": "pass1234", "name": "SS", "role": "cashier"})
        uid = r.json()["id"]
        tok = requests.post(f"{API}/auth/login", json={"email": email, "password": "pass1234"}).json()["token"]
        ch = {"Authorization": f"Bearer {tok}"}

        # no active shift
        r = requests.get(f"{API}/shifts/current", headers=ch)
        assert r.status_code == 200
        assert r.json() is None

        # open shift
        r = requests.post(f"{API}/shifts/open", headers=ch, json={"opening_cash": 50000})
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "open"
        assert r.json()["opening_cash"] == 50000

        # cannot open twice (400 or 409)
        r = requests.post(f"{API}/shifts/open", headers=ch, json={"opening_cash": 0})
        assert r.status_code in (400, 409)

        # create product and make a cash sale under this shift
        rp = requests.post(f"{API}/products", headers=admin_headers,
                           json={"name": "TEST_ShiftProd", "price": 5000, "cost": 2000, "stock": 10})
        p = rp.json()
        pay = {"items": [{"product_id": p["id"], "name": p["name"], "price": 5000, "cost": 2000, "qty": 2}],
               "payment_method": "cash", "amount_paid": 10000}
        rs = requests.post(f"{API}/sales", headers=ch, json=pay)
        assert rs.status_code == 200, rs.text

        # close shift with counted_cash matching expected
        # expected_cash = 50000 + 10000 = 60000, put counted = 60500 -> diff 500
        rc = requests.post(f"{API}/shifts/close", headers=ch, json={"counted_cash": 60500})
        assert rc.status_code == 200
        closed = rc.json()
        assert closed["status"] == "closed"
        assert closed["expected_cash"] == 60000
        assert closed["cash_sales"] == 10000
        assert closed["difference"] == 500

        # list shifts contains it
        rl = requests.get(f"{API}/shifts", headers=ch)
        assert rl.status_code == 200
        assert any(s["status"] == "closed" for s in rl.json())

        # close again -> 400
        rc2 = requests.post(f"{API}/shifts/close", headers=ch, json={"counted_cash": 0})
        assert rc2.status_code == 400

        # cleanup
        requests.delete(f"{API}/products/{p['id']}", headers=admin_headers)
        requests.delete(f"{API}/users/{uid}", headers=admin_headers)



# ---------------- Iteration 4: Settings (point_value & enable_shift_print) ----------------
class TestSettingsV4:
    def test_defaults_include_point_value_and_shift_print(self, admin_headers):
        r = requests.get(f"{API}/settings", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert "point_value" in d
        assert "enable_shift_print" in d
        # point_value default = 100 unless previously overwritten; must be a positive number
        assert isinstance(d["point_value"], (int, float))
        assert d["point_value"] > 0
        assert isinstance(d["enable_shift_print"], bool)

    def test_put_and_persist_new_fields(self, admin_headers):
        # baseline: get current settings so we don't clobber
        cur = requests.get(f"{API}/settings", headers=admin_headers).json()
        payload = dict(cur)
        payload["point_value"] = 200
        payload["enable_shift_print"] = False
        r = requests.put(f"{API}/settings", headers=admin_headers, json=payload)
        assert r.status_code == 200
        d = requests.get(f"{API}/settings", headers=admin_headers).json()
        assert d["point_value"] == 200
        assert d["enable_shift_print"] is False
        # restore defaults
        payload["point_value"] = 100
        payload["enable_shift_print"] = True
        requests.put(f"{API}/settings", headers=admin_headers, json=payload)


# ---------------- Iteration 4: Tukar Poin (redeem points) ----------------
class TestRedeemPoints:
    def _ensure_point_value(self, admin_headers, value=100):
        cur = requests.get(f"{API}/settings", headers=admin_headers).json()
        if cur.get("point_value") != value:
            cur["point_value"] = value
            requests.put(f"{API}/settings", headers=admin_headers, json=cur)

    def test_redeem_reduces_total_and_updates_net_points(self, admin_headers):
        self._ensure_point_value(admin_headers, 100)
        # Product Rp25.000
        p = requests.post(f"{API}/products", headers=admin_headers,
                          json={"name": "TEST_RedeemProd", "price": 25000, "cost": 10000, "stock": 20}).json()
        # Customer
        cust = requests.post(f"{API}/customers", headers=admin_headers,
                             json={"name": "TEST_Redeemer", "phone": ""}).json()
        cid = cust["id"]
        # First sale: earn 25 points on Rp25.000
        pay1 = {
            "items": [{"product_id": p["id"], "name": p["name"], "price": 25000, "cost": 10000, "qty": 1}],
            "payment_method": "cash", "amount_paid": 25000, "customer_id": cid,
        }
        s1 = requests.post(f"{API}/sales", headers=admin_headers, json=pay1)
        assert s1.status_code == 200, s1.text
        assert s1.json()["points_earned"] == 25
        # verify customer now has 25 points
        c1 = next(c for c in requests.get(f"{API}/customers", headers=admin_headers).json() if c["id"] == cid)
        assert c1["points"] == 25

        # Second sale: redeem 10 points -> Rp1.000 off
        pay2 = {
            "items": [{"product_id": p["id"], "name": p["name"], "price": 25000, "cost": 10000, "qty": 1}],
            "payment_method": "cash", "amount_paid": 24000, "customer_id": cid,
            "points_redeemed": 10,
        }
        s2 = requests.post(f"{API}/sales", headers=admin_headers, json=pay2)
        assert s2.status_code == 200, s2.text
        sale2 = s2.json()
        assert sale2["subtotal"] == 25000
        assert sale2["redeem_value"] == 1000
        assert sale2["points_redeemed"] == 10
        assert sale2["total"] == 24000
        # points_earned computed on final total after redemption: floor(24000/1000)=24
        assert sale2["points_earned"] == 24
        # final points = 25 - 10 + 24 = 39
        c2 = next(c for c in requests.get(f"{API}/customers", headers=admin_headers).json() if c["id"] == cid)
        assert c2["points"] == 39

        # cleanup
        requests.delete(f"{API}/customers/{cid}", headers=admin_headers)
        requests.delete(f"{API}/products/{p['id']}", headers=admin_headers)

    def test_over_redeem_returns_400(self, admin_headers):
        self._ensure_point_value(admin_headers, 100)
        p = requests.post(f"{API}/products", headers=admin_headers,
                          json={"name": "TEST_OverRedeemProd", "price": 5000, "cost": 2000, "stock": 5}).json()
        cust = requests.post(f"{API}/customers", headers=admin_headers,
                             json={"name": "TEST_LowPoints", "phone": ""}).json()
        cid = cust["id"]
        # customer starts with 0 points; try to redeem 5
        pay = {
            "items": [{"product_id": p["id"], "name": p["name"], "price": 5000, "cost": 2000, "qty": 1}],
            "payment_method": "cash", "amount_paid": 5000, "customer_id": cid,
            "points_redeemed": 5,
        }
        r = requests.post(f"{API}/sales", headers=admin_headers, json=pay)
        assert r.status_code == 400
        # cleanup
        requests.delete(f"{API}/customers/{cid}", headers=admin_headers)
        requests.delete(f"{API}/products/{p['id']}", headers=admin_headers)

    def test_redeem_requires_customer_or_ignored(self, admin_headers):
        # if no customer_id but points_redeemed>0 the backend should reject (400) OR silently ignore.
        self._ensure_point_value(admin_headers, 100)
        p = requests.post(f"{API}/products", headers=admin_headers,
                          json={"name": "TEST_NoCustRedeem", "price": 3000, "cost": 1000, "stock": 5}).json()
        pay = {
            "items": [{"product_id": p["id"], "name": p["name"], "price": 3000, "cost": 1000, "qty": 1}],
            "payment_method": "cash", "amount_paid": 3000,
            "points_redeemed": 5,
        }
        r = requests.post(f"{API}/sales", headers=admin_headers, json=pay)
        # Acceptable behaviors: 400 (rejects) OR 200 with redeem_value=0 (ignored)
        if r.status_code == 200:
            assert r.json().get("redeem_value", 0) == 0
        else:
            assert r.status_code == 400
        requests.delete(f"{API}/products/{p['id']}", headers=admin_headers)



# ---------------- Iteration 5: ESC/POS Print ----------------
import base64 as _b64


class TestPrint:
    def _make_sale(self, admin_headers):
        p = requests.post(f"{API}/products", headers=admin_headers,
                          json={"name": "TEST_PrintProd", "price": 12345, "cost": 5000, "stock": 20}).json()
        pay = {
            "items": [{"product_id": p["id"], "name": p["name"], "price": 12345, "cost": 5000, "qty": 2}],
            "payment_method": "cash", "amount_paid": 30000,
        }
        s = requests.post(f"{API}/sales", headers=admin_headers, json=pay)
        assert s.status_code == 200, s.text
        return p["id"], s.json()["id"]

    def test_print_bytes_contains_store_and_cut(self, admin_headers):
        pid, sid = self._make_sale(admin_headers)
        r = requests.get(f"{API}/print/{sid}", headers=admin_headers)
        assert r.status_code == 200, r.text
        data = r.json().get("data")
        assert isinstance(data, str) and len(data) > 0
        raw = _b64.b64decode(data)
        assert len(raw) > 100
        # Store name
        assert b"Mandiri POS" in raw or b"TEST_PrintProd" in raw
        # Item name should appear
        assert b"TEST_PrintProd" in raw
        # TOTAL label
        assert b"TOTAL" in raw
        # GS V paper cut command
        assert b"\x1d\x56" in raw
        # cleanup
        requests.delete(f"{API}/products/{pid}", headers=admin_headers)

    def test_print_bytes_404_for_unknown_sale(self, admin_headers):
        r = requests.get(f"{API}/print/507f1f77bcf86cd799439011", headers=admin_headers)
        assert r.status_code == 404

    def test_print_bytes_requires_auth(self):
        r = requests.get(f"{API}/print/507f1f77bcf86cd799439011")
        assert r.status_code in (401, 403)

    def test_network_print_no_ip_configured_returns_400(self, admin_headers):
        # Ensure printer_ip empty in settings
        cur = requests.get(f"{API}/settings", headers=admin_headers).json()
        original_ip = cur.get("printer_ip", "")
        original_port = cur.get("printer_port", 9100)
        cur["printer_ip"] = ""
        requests.put(f"{API}/settings", headers=admin_headers, json=cur)

        pid, sid = self._make_sale(admin_headers)
        r = requests.post(f"{API}/print/{sid}/network", headers=admin_headers, json={})
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "IP printer" in detail or "belum diatur" in detail

        # restore
        cur["printer_ip"] = original_ip
        cur["printer_port"] = original_port
        requests.put(f"{API}/settings", headers=admin_headers, json=cur)
        requests.delete(f"{API}/products/{pid}", headers=admin_headers)

    def test_network_print_unreachable_ip_returns_400(self, admin_headers):
        pid, sid = self._make_sale(admin_headers)
        r = requests.post(f"{API}/print/{sid}/network", headers=admin_headers,
                          json={"ip": "192.168.1.250", "port": 9100})
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "Gagal terhubung" in detail
        requests.delete(f"{API}/products/{pid}", headers=admin_headers)


class TestPrinterSettings:
    def test_defaults_include_printer_fields(self, admin_headers):
        r = requests.get(f"{API}/settings", headers=admin_headers)
        assert r.status_code == 200
        d = r.json()
        assert "printer_ip" in d
        assert "printer_port" in d
        assert isinstance(d["printer_port"], int)

    def test_put_printer_fields_persist_admin(self, admin_headers):
        cur = requests.get(f"{API}/settings", headers=admin_headers).json()
        original_ip = cur.get("printer_ip", "")
        original_port = cur.get("printer_port", 9100)
        cur["printer_ip"] = "10.0.0.99"
        cur["printer_port"] = 9101
        r = requests.put(f"{API}/settings", headers=admin_headers, json=cur)
        assert r.status_code == 200
        d = requests.get(f"{API}/settings", headers=admin_headers).json()
        assert d["printer_ip"] == "10.0.0.99"
        assert d["printer_port"] == 9101
        # restore (spec says reset printer_ip to '' after testing)
        cur["printer_ip"] = ""
        cur["printer_port"] = 9100
        requests.put(f"{API}/settings", headers=admin_headers, json=cur)
        d2 = requests.get(f"{API}/settings", headers=admin_headers).json()
        assert d2["printer_ip"] == ""
        assert d2["printer_port"] == 9100

    def test_cashier_cannot_put_printer_settings(self, admin_headers):
        email = f"test_prn_cashier_{int(time.time())}@example.com"
        requests.post(f"{API}/auth/register", headers=admin_headers,
                      json={"email": email, "password": "pass1234", "name": "PRNC", "role": "cashier"})
        tok = requests.post(f"{API}/auth/login", json={"email": email, "password": "pass1234"}).json()["token"]
        ch = {"Authorization": f"Bearer {tok}"}
        cur = requests.get(f"{API}/settings", headers=ch).json()
        cur["printer_ip"] = "10.0.0.5"
        r = requests.put(f"{API}/settings", headers=ch, json=cur)
        assert r.status_code == 403
