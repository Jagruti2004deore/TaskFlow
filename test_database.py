
import database
import tempfile
from pathlib import Path


def test_task_database():
    # Use a temporary database so the real tasks.db stays untouched.
    with tempfile.TemporaryDirectory() as temp_dir:
        test_db = Path(temp_dir) / "test_tasks.db"
        database.DATABASE_NAME = str(test_db)

        database.create_users_table()
        database.create_table()

        # Create a test user to own the task.
        user_id = database.create_user(
            "Test User",
            "testuser@example.com",
            "test_password_hash",
        )

        # Add a task belonging to this user.
        task_id = database.add_task_to_db(
            "TaskFlow database test",
            user_id,
        )

        tasks = database.get_all_tasks(user_id)
        print("Saved tasks:", tasks)

        assert len(tasks) == 1
        assert tasks[0][0] == task_id

        # Update the task for the same user.
        updated = database.update_task_in_db(
            task_id,
            "Done",
            user_id,
        )
        print("Task updated:", updated)
        assert updated is True

        tasks = database.get_all_tasks(user_id)
        print("Latest task:", tasks[-1])
        assert tasks[-1][2] == "Done"

        # Another user must not be able to update this task.
        other_user_id = database.create_user(
            "Another User",
            "another@example.com",
            "another_password_hash",
        )

        other_user_tasks = database.get_all_tasks(other_user_id)
        assert other_user_tasks == []

        unauthorized_update = database.update_task_in_db(
            task_id,
            "In Progress",
            other_user_id,
        )
        assert unauthorized_update is False

        print("Task ownership check passed.")
