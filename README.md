# PythonBlockbusters

A Flask web application for managing a video rental store chain. Built on top of a MySQL database, it provides dashboards, film browsing, customer management, rental tracking, and payment processing across multiple store locations.

## Features

- **Dashboard** -- Real-time stats including today's rentals, revenue, active/overdue rentals, and charts (top films, rentals by category, revenue trends, inventory by rating)
- **Films** -- Browse the film catalogue with thumbnails, filter by category/rating/store, and view detailed film info
- **Customers** -- List, search, add, and edit customers with avatar support
- **Rentals** -- Create new rentals, track active and overdue rentals, process returns
- **Payments** -- View and manage payment records
- **Staff** -- Staff management for admin users
- **Authentication** -- Role-based access (admin, staff, customer) with login/registration
- **Multi-store** -- Each store has a name and icon; data can be filtered by store

## Tech Stack

- **Backend:** Python 3.9 / Flask 3.1
- **Database:** MySQL (via PyMySQL)
- **Frontend:** Jinja2 templates, Bootstrap, Chart.js
- **Auth:** SHA-256 password hashing, session-based authentication

## Prerequisites

- Python 3.9+
- MySQL server with a Sakila-based database

## Setup

1. **Clone the repository**

   ```bash
   git clone <repo-url>
   cd PythonBlockbusters
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure the database connection**

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

4. **Run the database setup script**

   This creates the `app_users` table, assigns store names, and creates default admin/staff accounts:

   ```bash
   python setup_db.py
   ```

5. **Start the application**

   ```bash
   python app.py
   ```

   The app will be available at `http://localhost:8080`.

## Default Accounts

| Role  | Username | Password     |
|-------|----------|--------------|
| Admin | admin    | Admin@1234   |
| Staff | *(email prefix)* | Staff@1234 |

## Project Structure

```
PythonBlockbusters/
├── app.py                  # Flask app factory and startup
├── db.py                   # Database connection and query helpers
├── setup_db.py             # One-time DB setup (users, store names)
├── config.json             # Database and app configuration
├── requirements.txt        # Python dependencies
├── routes/
│   ├── auth.py             # Login, logout, registration, role checks
│   ├── dashboard.py        # Dashboard stats and detail views
│   ├── films.py            # Film listing and detail pages
│   ├── customers.py        # Customer CRUD
│   ├── rentals.py          # Rental management
│   ├── payments.py         # Payment records
│   └── staff.py            # Staff management
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── films.html
│   ├── customers.html
│   ├── rentals.html
│   └── ...
└── static/
    ├── avatars/            # Customer avatar images
    ├── thumbnails/         # Film thumbnail images
    ├── store_icons/        # SVG icons for each store
    └── favicon.svg
```
