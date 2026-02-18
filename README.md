# 🎬 PythonBlockbusters

A full-featured Flask web application for managing a chain of video rental stores. Built on top of a MySQL database (Sakila schema), it provides role-based dashboards, film browsing with recommendations, customer and staff management, rental tracking with late fee calculation, and payment processing -- all across multiple named store locations.

## ✨ Features

### 📊 Dashboard (Admin/Staff)
- **Stat cards** showing today's rentals, today's revenue, active rentals, overdue rentals, total revenue, and total rentals -- each clickable to view the underlying records
- **Summary row** with total customers, films, and inventory counts
- **Charts** powered by Chart.js:
  - 🏆 Top 10 most rented films (horizontal bar)
  - 📁 Rentals by category (doughnut)
  - 📈 Revenue trend (line chart with 1M / 6M / 1Y / 5Y / 10Y period selector)
  - ⭐ Inventory by rating (pie)
- Stats are fetched asynchronously via a `/api/dashboard/stats` JSON endpoint

### 🏠 Dashboard (Customer)
- Personal overview showing active rentals, total rental history count, and total amount spent

### 🎥 Films
- Full film catalogue with thumbnail images
- 🔍 **Search** by title or description
- 🏷️ **Filter** by category, MPAA rating, and release year
- 📄 **Film detail page** with full metadata (language, duration, rental rate, replacement cost, special features), cast list, per-store inventory availability, and "customers who rented this also rented" recommendations

### 👥 Customers (Admin/Staff only)
- List all customers with search by name or email
- 📋 **Customer detail page** showing profile with avatar, store assignment, total rentals, active rentals, total spent, favourite category, top 5 categories chart, and recent rental history
- ➕ **Add** new customers (creates both a customer record and a login account)
- ✏️ **Edit** customer details (name, email, store, active status)
- 🚫 **Deactivate** customers (admin only) -- soft delete that also removes their login

### 📀 Rentals
- 👔 **Staff/Admin view**: list all rentals with search by film title or customer name (limited to 500 most recent)
- 👤 **Customer view**: list their own rentals
- 📝 **New rental form** (admin/staff): select customer, film, and store; checks inventory availability via `/api/inventory/<film_id>/<store_id>` before creating
- ↩️ **Return a rental**: calculates payment automatically using the film's base rental rate plus a 💲1.00/day late fee for overdue returns

### 💳 Payments (Admin/Staff only)
- List all payments with search by customer name or film title
- 📅 **Date range filter** to narrow results
- 💰 Running total of displayed payments

### 🪪 Staff (Admin only)
- List all staff members with their linked usernames and store assignments
- ➕ **Add** new staff (creates both a staff record and a login account with bcrypt-hashed password)
- ✏️ **Edit** staff details (name, email, store, active status)
- 🚫 **Deactivate** staff members

### 🔐 Authentication & Authorization
- 🔑 **Login** with username and password (SHA-256 for legacy accounts, bcrypt for new accounts)
- 📝 **Registration** for new customers (creates a customer record and login automatically)
- 🎭 **Three roles**: `admin`, `staff`, `customer` -- each with different navigation and access levels
- 🛡️ Session-based authentication with `login_required` and `role_required` decorators
- ✅ **Password validation**: minimum 8 characters, must include uppercase, lowercase, digit, and special character

### 🎨 UI / UX
- 🌗 **Dark/light theme toggle** persisted to localStorage
- 📱 Responsive Bootstrap 5.3 layout with a fixed sidebar navigation
- 🏪 Store icons (SVG) displayed alongside store names throughout the app
- 🖼️ Customer avatars and film thumbnails (auto-generated PNGs)
- 💬 Flash messages for success, error, and info feedback
- 👁️ Global page view counter displayed in the footer

### 🏬 Multi-Store
- 25 named stores (Action Replay, Cinefile, Five Star Films, Flicks, Golden Reel Rentals, Hollywood Hits, etc.)
- 🎨 Each store has a custom SVG icon
- 🏷️ Store names are used in place of store IDs throughout the UI

## 🛠️ Tech Stack

| Layer     | Technology                                      |
|-----------|-------------------------------------------------|
| 🐍 Backend   | Python 3.9, Flask 3.1                           |
| 🗄️ Database  | MySQL (via PyMySQL 1.1, DictCursor)             |
| 📄 Templates | Jinja2                                          |
| 🎨 Frontend  | Bootstrap 5.3, Bootstrap Icons, Chart.js 4.4    |
| 🔒 Auth      | SHA-256 (legacy) / bcrypt 4.2 (new accounts)    |
| 🔐 Crypto    | cryptography 44.0 (PyMySQL SSL support)         |

## 📋 Prerequisites

- 🐍 Python 3.9+
- 🗄️ MySQL 5.7+ or 8.0+ with a Sakila-based database loaded
- The database must contain the standard Sakila tables: `film`, `actor`, `category`, `inventory`, `rental`, `payment`, `customer`, `staff`, `store`, `address`, `city`, `language`, plus a `v_users` view that unions `app_users` with relevant profile data

## 🚀 Setup

1. **📥 Clone the repository**

   ```bash
   git clone https://github.com/DavidAyliffe/PythonBlockbusters.git
   cd PythonBlockbusters
   ```

2. **📦 Create a virtual environment and install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   # .venv\Scripts\activate         # Windows
   pip install -r requirements.txt
   ```

3. **⚙️ Configure the database connection**

   Edit `config.json` with your MySQL credentials:

   ```json
   {
     "db": {
       "host": "localhost",
       "port": 3306,
       "user": "root",
       "password": "your-password",
       "database": "your_database"
     },
     "secret_key": "change-this-to-a-random-secret-key",
     "admin_username": "admin",
     "admin_password": "Admin@1234"
   }
   ```

4. **🗄️ Run the database setup script**

   This creates the `app_users` table, adds a `name` column to the `store` table, assigns names to all stores, and creates default admin and staff accounts:

   ```bash
   python setup_db.py
   ```

5. **🖼️ Generate static assets (optional)**

   If you need to regenerate customer avatars or film thumbnails:

   ```bash
   python generate_avatars.py
   python generate_thumbnails.py
   ```

6. **▶️ Start the application**

   ```bash
   python app.py
   ```

   The app runs on `http://localhost:8080` with debug mode enabled.

## 👤 Default Accounts

| Role  | Username              | Password     |
|-------|-----------------------|--------------|
| 🛡️ Admin | admin                 | Admin@1234   |
| 👔 Staff | *(email prefix)*      | Staff@1234   |

Staff accounts are auto-created from existing staff records in the database. The username is the part of their email before the `@`.

## 🔌 API Endpoints

| Endpoint                                | Method | Auth     | Description                            |
|-----------------------------------------|--------|----------|----------------------------------------|
| `/api/dashboard/stats`                  | GET    | 🔒 Login | 📊 Dashboard summary stats and chart data |
| `/api/dashboard/revenue_trend?period=`  | GET    | 🔒 Login | 📈 Revenue trend data (1m/6m/1y/5y/10y)  |
| `/api/inventory/<film_id>/<store_id>`   | GET    | 🔒 Login | 📦 Check available copies at a store      |

## 📁 Project Structure

```
PythonBlockbusters/
├── 🏭 app.py                   # Flask app factory, template filters, startup
├── 🗄️ db.py                    # Database helpers: get_connection(), query(), execute()
├── ⚙️ setup_db.py              # One-time setup: app_users table, store names, default accounts
├── 📝 config.json              # Database credentials and app configuration
├── 📦 requirements.txt         # Python dependencies
├── 🖼️ generate_avatars.py      # Script to generate customer avatar PNGs
├── 🎞️ generate_thumbnails.py   # Script to generate film thumbnail PNGs
│
├── 🛣️ routes/
│   ├── 🔐 auth.py              # Login, logout, registration, decorators, validation
│   ├── 📊 dashboard.py         # Dashboard stats, charts, detail drill-down views
│   ├── 🎥 films.py             # Film listing (search/filter) and detail page
│   ├── 👥 customers.py         # Customer CRUD with detail profiles
│   ├── 📀 rentals.py           # Rental listing, creation, return with payment
│   ├── 💳 payments.py          # Payment listing with search and date filters
│   └── 🪪 staff.py             # Staff CRUD (admin only)
│
├── 🎨 templates/
│   ├── base.html               # Layout: sidebar, theme toggle, flash messages, footer
│   ├── login.html              # Login form
│   ├── register.html           # Registration form
│   ├── dashboard.html          # Admin/staff dashboard with stat cards and charts
│   ├── customer_dashboard.html # Customer personal dashboard
│   ├── dashboard_detail.html   # Drill-down view for dashboard stats
│   ├── films.html              # Film catalogue with filters
│   ├── film_detail.html        # Individual film page
│   ├── customers.html          # Customer list
│   ├── customer_detail.html    # Customer profile page
│   ├── customer_form.html      # Add/edit customer form
│   ├── rentals.html            # Rental list
│   ├── rental_form.html        # New rental form
│   ├── payments.html           # Payment list
│   ├── staff.html              # Staff list
│   └── staff_form.html         # Add/edit staff form
│
└── 📂 static/
    ├── 👤 avatars/             # 599 customer avatar PNGs (1.png - 599.png)
    ├── 🎞️ thumbnails/          # 1000 film thumbnail PNGs (1.png - 1000.png)
    ├── 🏪 store_icons/         # 25 store SVG icons
    └── ⭐ favicon.svg          # App favicon
```
