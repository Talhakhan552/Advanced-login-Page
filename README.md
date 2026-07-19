
# 🔐 Advanced Login & Authentication System

A professional-grade, full-stack authentication system built with Python, PostgreSQL, and React. This project demonstrates industry-standard security practices, including JWT-based session management, Role-Based Access Control (RBAC), and secure password hashing.

## 🚀 Features

* **Secure Authentication**: Password hashing using `bcrypt` and JWT (JSON Web Token) access/refresh token rotation.
* **Role-Based Access Control (RBAC)**: Distinct permissions for `Admin`, `Moderator`, and `Regular User` roles.
* **Protected Routes**: Frontend and backend protection ensuring only authorized users can access sensitive data.
* **Full-Stack Separation**: Decoupled Python Flask backend and React frontend with proxy configuration.
* **Persistent Data**: PostgreSQL database for robust user and role management.

## 🛠 Tech Stack

* **Backend**: Python, Flask, `flask-cors`, `psycopg2`, `PyJWT`, `bcrypt`.
* **Frontend**: React, `react-router-dom`.
* **Database**: PostgreSQL & pgAdmin 4.
* **Environment**: Designed for Windows/Local development with virtual environments.

## 📦 Getting Started

### Prerequisites

* Python 3.8+
* PostgreSQL & pgAdmin 4
* Node.js (for React)

### 1. Database Setup

1. Open **pgAdmin 4** and create a database named `login_system`.
2. Open the **Query Tool** and execute the contents of `schema.sql` to initialize your tables.

### 2. Backend Setup

1. Navigate to the project root and create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate

```


2. Install dependencies:
```bash
pip install flask flask-cors psycopg2-binary pyjwt bcrypt python-dotenv

```


3. Create a `.env` file in the root folder and add your PostgreSQL credentials:
```env
DB_PASSWORD=your_actual_password
SECRET_KEY=your_generated_random_secret_key

```


4. Run the server:
```bash
python app.py

```



### 3. Frontend Setup

1. Navigate to the `frontend` folder:
```bash
cd frontend
npm install

```


2. Create a `.env` file in the `frontend/` folder:
```env
REACT_APP_API_URL=http://localhost:5000

```


3. Start the development server:
```bash
npm start

```



## 🔑 Demo Credentials

You can log in with the following users after running the SQL scripts:

* **Admin**: `john_admin` / `password123`
* **User**: `jane_user` / `password123`
* **Moderator**: `bob_mod` / `password123`

## 🛡 Security Note

* **Never** share your `SECRET_KEY` or PostgreSQL passwords.
* Ensure your `.gitignore` file includes `.env` and `node_modules/` to prevent sensitive data and heavy dependency folders from being uploaded to GitHub

---

*Built as a comprehensive study on full-stack web security and system architecture.*