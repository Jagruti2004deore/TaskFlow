
import os
import sqlite3

DATABASE_NAME = os.getenv("TASKFLOW_DATABASE", "tasks.db")



from contextlib import contextmanager


@contextmanager
def connect_db():
    """Open a database connection and close it after use."""
    connection = sqlite3.connect(DATABASE_NAME)

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()



def create_table():
    """Create or safely migrate the tasks table."""
    with connect_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'To Do',
                owner_id INTEGER REFERENCES users(id)
            )
        """)

        # Support databases created before task ownership existed.
        columns = connection.execute(
            "PRAGMA table_info(tasks)"
        ).fetchall()

        column_names = [column[1] for column in columns]

        if "owner_id" not in column_names:
            connection.execute(
                "ALTER TABLE tasks ADD COLUMN owner_id INTEGER REFERENCES users(id)"
            )




def add_task_to_db(title, owner_id):
    """Insert a task for a specific user and return its ID."""
    with connect_db() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, owner_id) VALUES (?, ?)",
            (title, owner_id)
        )
        return cursor.lastrowid


def get_all_tasks(owner_id):
    """Return only the tasks belonging to a specific user."""
    with connect_db() as connection:
        return connection.execute(
            """
            SELECT id, title, status
            FROM tasks
            WHERE owner_id = ?
            ORDER BY id
            """,
            (owner_id,)
        ).fetchall()


def update_task_in_db(task_id, status, owner_id):
    """Update a task only if it belongs to the specified user."""
    with connect_db() as connection:
        cursor = connection.execute(
            """
            UPDATE tasks
            SET status = ?
            WHERE id = ? AND owner_id = ?
            """,
            (status, task_id, owner_id)
        )
        return cursor.rowcount > 0


def delete_task_from_db(task_id, owner_id):
    """Delete a task only if it belongs to the specified user."""
    with connect_db() as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ? AND owner_id = ?",
            (task_id, owner_id)
        )
        return cursor.rowcount > 0


def get_tasks_by_status(status, owner_id):
    """Return a user's tasks matching a specific status."""
    with connect_db() as connection:
        return connection.execute(
            """
            SELECT id, title, status
            FROM tasks
            WHERE status = ? AND owner_id = ?
            ORDER BY id
            """,
            (status, owner_id)
        ).fetchall()


def search_tasks(owner_id, search=None, status=None, limit=10, offset=0):
    """Search and filter only the specified user's tasks."""
    query = """
        SELECT id, title, status
        FROM tasks
        WHERE owner_id = ?
    """
    parameters = [owner_id]

    if search:
        query += " AND title LIKE ?"
        parameters.append(f"%{search}%")

    if status:
        query += " AND status = ?"
        parameters.append(status)

    query += " ORDER BY id LIMIT ? OFFSET ?"
    parameters.extend([limit, offset])

    with connect_db() as connection:
        return connection.execute(query, parameters).fetchall()

    

def create_users_table():
    """Create the users table if it does not exist."""
    with connect_db() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                hashed_password TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    

def assign_unowned_tasks_to_existing_user():
    """Assign legacy tasks to the first registered user, if one exists."""
    with connect_db() as connection:
        user = connection.execute(
            "SELECT id FROM users ORDER BY id LIMIT 1"
        ).fetchone()

        if user is None:
            return 0

        cursor = connection.execute(
            "UPDATE tasks SET owner_id = ? WHERE owner_id IS NULL",
            (user[0],),
        )

        return cursor.rowcount



def create_user(username, email, hashed_password):
    """Save a new user and return the new user's ID."""
    with connect_db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (username, email, hashed_password)
            VALUES (?, ?, ?)
            """,
            (username, email, hashed_password)
        )
        return cursor.lastrowid


def get_user_by_email(email):
    """Find a user by email address."""
    with connect_db() as connection:
        return connection.execute(
            """
            SELECT id, username, email, hashed_password, created_at
            FROM users
            WHERE email = ?
            """,
            (email,)
        ).fetchone()


