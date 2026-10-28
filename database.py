# database.py
# This file handles all communication with the SQLite database.

import sqlite3
import os
from datetime import date

# The database will live inside a folder called "data".
# We build the path using os.path.join so it works correctly on Windows.
DATA_FOLDER = "data"
DB_PATH = os.path.join(DATA_FOLDER, "business.db")


def get_connection():
    """
    Open a connection to the database.
    - Creates the 'data' folder if it does not exist yet.
    - Turns on foreign key enforcement (SQLite needs this turned on per connection).
    - Uses sqlite3.Row so we can access columns by name, like row["name"].
    """
    os.makedirs(DATA_FOLDER, exist_ok=True)  # create data/ if missing
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # access columns by name
    conn.execute("PRAGMA foreign_keys = ON")  # enforce foreign keys
    return conn


def init_db():
    """
    Create the tables if they do not exist.
    'IF NOT EXISTS' means it is safe to run this every time the app starts.
    Existing data is never deleted.
    """
    conn = get_connection()
    cur = conn.cursor()

    # ---------- CLIENTS TABLE ----------
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            company TEXT,
            email TEXT,
            phone TEXT,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # ---------- PROJECTS TABLE ----------
    # client_id links each project to a client.
    # ON DELETE SET NULL: if the client is deleted, the project stays but becomes unassigned.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            start_date TEXT,
            deadline TEXT,
            budget REAL DEFAULT 0,
            status TEXT DEFAULT 'Planned',
            progress INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE SET NULL
        )
    """)

    # ---------- TASKS TABLE ----------
    # project_id links each task to a project.
    # ON DELETE CASCADE: if the project is deleted, its tasks are deleted too
    # (the app will warn the user before this happens).
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            deadline TEXT,
            priority TEXT DEFAULT 'Medium',
            status TEXT DEFAULT 'To Do',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# =====================================================================
# CLIENT FUNCTIONS
# =====================================================================

def create_client(name, company, email, phone, notes):
    """Insert a new client. The ? placeholders are filled safely."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO clients (name, company, email, phone, notes) VALUES (?, ?, ?, ?, ?)",
        (name, company, email, phone, notes),
    )
    conn.commit()
    conn.close()


def get_clients(search=""):
    """
    Return all clients. If 'search' is given, filter by name, company, or email.
    Results are sorted alphabetically by name.
    """
    conn = get_connection()
    if search:
        like = f"%{search}%"
        rows = conn.execute(
            """SELECT * FROM clients
               WHERE name LIKE ? OR company LIKE ? OR email LIKE ?
               ORDER BY name""",
            (like, like, like),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
    conn.close()
    return rows


def get_client(client_id):
    """Return one client by id, or None if not found."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    conn.close()
    return row


def update_client(client_id, name, company, email, phone, notes):
    """Update an existing client's details."""
    conn = get_connection()
    conn.execute(
        "UPDATE clients SET name=?, company=?, email=?, phone=?, notes=? WHERE id=?",
        (name, company, email, phone, notes, client_id),
    )
    conn.commit()
    conn.close()


def delete_client(client_id):
    """
    Delete a client. Projects linked to this client are kept,
    but their client_id becomes NULL (unassigned) because of ON DELETE SET NULL.
    """
    conn = get_connection()
    conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
    conn.commit()
    conn.close()


def count_projects_for_client(client_id):
    """Count how many projects belong to a client (used for delete warnings)."""
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE client_id = ?", (client_id,)
    ).fetchone()[0]
    conn.close()
    return count


# =====================================================================
# PROJECT FUNCTIONS
# =====================================================================

def create_project(client_id, name, description, start_date, deadline,
                   budget, status, progress):
    """Insert a new project."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO projects
           (client_id, name, description, start_date, deadline, budget, status, progress)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (client_id, name, description, start_date, deadline, budget, status, progress),
    )
    conn.commit()
    conn.close()


def get_projects(status=None, client_id=None):
    """
    Return projects with the client's name attached.
    Optional filters: status and/or client_id.
    LEFT JOIN keeps projects that have no client.
    """
    conn = get_connection()
    query = """
        SELECT p.*, c.name AS client_name
        FROM projects p
        LEFT JOIN clients c ON p.client_id = c.id
    """
    conditions = []
    params = []
    if status:
        conditions.append("p.status = ?")
        params.append(status)
    if client_id:
        conditions.append("p.client_id = ?")
        params.append(client_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    # NULL deadlines go last so projects with real deadlines appear first
    query += " ORDER BY p.deadline IS NULL, p.deadline"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_project(project_id):
    """Return one project with its client name, or None."""
    conn = get_connection()
    row = conn.execute(
        """SELECT p.*, c.name AS client_name
           FROM projects p
           LEFT JOIN clients c ON p.client_id = c.id
           WHERE p.id = ?""",
        (project_id,),
    ).fetchone()
    conn.close()
    return row


def update_project(project_id, client_id, name, description, start_date,
                   deadline, budget, status, progress):
    """Update an existing project."""
    conn = get_connection()
    conn.execute(
        """UPDATE projects
           SET client_id=?, name=?, description=?, start_date=?, deadline=?,
               budget=?, status=?, progress=?
           WHERE id=?""",
        (client_id, name, description, start_date, deadline,
         budget, status, progress, project_id),
    )
    conn.commit()
    conn.close()


def delete_project(project_id):
    """Delete a project. Its tasks are deleted automatically (ON DELETE CASCADE)."""
    conn = get_connection()
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


def count_tasks_for_project(project_id):
    """Count tasks in a project (used for delete warnings)."""
    conn = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchone()[0]
    conn.close()
    return count


# =====================================================================
# TASK FUNCTIONS
# =====================================================================

def create_task(project_id, title, description, deadline, priority, status):
    """Insert a new task."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO tasks (project_id, title, description, deadline, priority, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (project_id, title, description, deadline, priority, status),
    )
    conn.commit()
    conn.close()


def get_tasks(project_id=None, priority=None, status=None):
    """
    Return tasks with the project name attached.
    Optional filters: project_id, priority, status.
    """
    conn = get_connection()
    query = """
        SELECT t.*, p.name AS project_name
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
    """
    conditions = []
    params = []
    if project_id:
        conditions.append("t.project_id = ?")
        params.append(project_id)
    if priority:
        conditions.append("t.priority = ?")
        params.append(priority)
    if status:
        conditions.append("t.status = ?")
        params.append(status)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY t.deadline IS NULL, t.deadline"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_task(task_id):
    """Return one task with its project name, or None."""
    conn = get_connection()
    row = conn.execute(
        """SELECT t.*, p.name AS project_name
           FROM tasks t
           LEFT JOIN projects p ON t.project_id = p.id
           WHERE t.id = ?""",
        (task_id,),
    ).fetchone()
    conn.close()
    return row


def update_task(task_id, project_id, title, description, deadline, priority, status):
    """Update an existing task."""
    conn = get_connection()
    conn.execute(
        """UPDATE tasks
           SET project_id=?, title=?, description=?, deadline=?, priority=?, status=?
           WHERE id=?""",
        (project_id, title, description, deadline, priority, status, task_id),
    )
    conn.commit()
    conn.close()


def delete_task(task_id):
    """Delete a task."""
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


# =====================================================================
# DASHBOARD / REPORT HELPER FUNCTIONS
# =====================================================================

def get_dashboard_counts():
    """
    Return a dictionary with the six summary numbers used on the dashboard.
    Overdue = deadline is before today AND status is not Completed.
    """
    today = date.today().isoformat()  # e.g. "2025-06-01"
    conn = get_connection()

    total_clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
    total_projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    active_projects = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE status = 'In Progress'"
    ).fetchone()[0]
    completed_projects = conn.execute(
        "SELECT COUNT(*) FROM projects WHERE status = 'Completed'"
    ).fetchone()[0]
    pending_tasks = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE status != 'Completed'"
    ).fetchone()[0]
    overdue_tasks = conn.execute(
        """SELECT COUNT(*) FROM tasks
           WHERE status != 'Completed'
             AND deadline IS NOT NULL
             AND deadline < ?""",
        (today,),
    ).fetchone()[0]

    conn.close()
    return {
        "total_clients": total_clients,
        "total_projects": total_projects,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
    }


def get_project_status_counts():
    """Return a dict like {'Planned': 2, 'In Progress': 3, ...}."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM projects GROUP BY status"
    ).fetchall()
    conn.close()
    return {row["status"]: row["count"] for row in rows}


def get_task_status_counts():
    """Return a dict like {'To Do': 5, 'In Progress': 2, 'Completed': 4}."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, COUNT(*) AS count FROM tasks GROUP BY status"
    ).fetchall()
    conn.close()
    return {row["status"]: row["count"] for row in rows}


def get_upcoming_deadlines(limit=10):
    """
    Return the next deadlines from BOTH projects and tasks (not completed),
    sorted by date. Each row has: type, title, deadline, status.
    """
    today = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT 'Project' AS type, name AS title, deadline, status
        FROM projects
        WHERE deadline IS NOT NULL AND deadline >= ?
        UNION ALL
        SELECT 'Task' AS type, title, deadline, status
        FROM tasks
        WHERE deadline IS NOT NULL AND deadline >= ? AND status != 'Completed'
        ORDER BY deadline
        LIMIT ?
        """,
        (today, today, limit),
    ).fetchall()
    conn.close()
    return rows


def get_overdue_tasks(limit=10):
    """Return tasks whose deadline has passed and are not completed."""
    today = date.today().isoformat()
    conn = get_connection()
    rows = conn.execute(
        """SELECT t.*, p.name AS project_name
           FROM tasks t
           LEFT JOIN projects p ON t.project_id = p.id
           WHERE t.status != 'Completed'
             AND t.deadline IS NOT NULL
             AND t.deadline < ?
           ORDER BY t.deadline
           LIMIT ?""",
        (today, limit),
    ).fetchall()
    conn.close()
    return rows


def get_budget_total():
    """Return the sum of all estimated project budgets."""
    conn = get_connection()
    total = conn.execute(
        "SELECT COALESCE(SUM(budget), 0) FROM projects"
    ).fetchone()[0]
    conn.close()
    return total


# =====================================================================
# If you run this file directly, create the database and print a message.
# =====================================================================
if __name__ == "__main__":
    init_db()
    print("Database created / checked successfully.")
    print("Database file location:", DB_PATH)