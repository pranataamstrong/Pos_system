# Mandiri POS — PRD

## Problem Statement
"Buatkan saya POS system dengan report yang lengkap, serupa dengan Loyverse POS namun bisa mandiri untuk saya pribadi dan bisa langsung digunakan."

## Architecture
- Backend: FastAPI + MongoDB (motor). All routes under `/api`. JWT auth (Bearer token in login response body, stored in localStorage on frontend).
- Frontend: React + React Router + shadcn/ui + recharts + sonner. Split-screen POS, analytics dashboard.
- Language: Bahasa Indonesia. Currency: Rupiah (Rp).

## User Personas
- Owner/Admin: full access (POS, reports, products, categories, users, history).
- Kasir (Cashier): POS + transaction history only.

## Core Requirements (static)
- JWT login, role-based access (admin/cashier).
- POS cashier: product grid, category filter, search, cart, checkout (Tunai/Kartu/QRIS), discount, change calc, receipt + print.
- Product & category management (CRUD) with stock/inventory and cost (modal) for profit.
- Complete reports: sales summary, sales over time, top products, sales by category, payment method breakdown, low stock.
- Transaction history with receipt detail.
- User management (admin adds cashiers).

## Implemented (2026-06)
- Auth: login/me/register(admin), JWT Bearer, admin seed (pranataamstrong@gmail.com / admin123). [done]
- POS checkout with stock reduction, subtotal/discount/total/profit/change. [done]
- Products, Categories, Users CRUD (admin-gated). [done]
- Reports dashboard with recharts (all 6 report endpoints). [done]
- History page with receipt detail + print. [done]
- Auto-seeded demo data (3 categories, 10 products). [done]
- Tested: 20/20 backend pytest pass, full frontend flow verified.

## Backlog / Next
- P1: Validate stock availability before checkout (currently allows negative stock).
- P1: Add Dialog aria-describedby to remove a11y console warnings.
- P2: Export reports to CSV/PDF.
- P2: Barcode scanning / SKU quick-add.
- P2: Multi-outlet / shift management.
- P2: Editable receipt header (store name, address).
