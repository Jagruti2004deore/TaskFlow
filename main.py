
from database import (
    create_table,
    add_task_to_db,
    get_all_tasks,
    update_task_in_db
)


def add_task():
    title = input("Enter task title: ").strip()

    if not title:
        print("Task title cannot be empty.")
        return

    add_task_to_db(title)
    print("Task added successfully!")


def view_tasks():
    tasks = get_all_tasks()

    if not tasks:
        print("No tasks available.")
        return

    for task in tasks:
        print(
            f"ID: {task[0]} | "
            f"Title: {task[1]} | "
            f"Status: {task[2]}"
        )


def update_task_status():
    try:
        task_id = int(input("Enter task ID: "))
    except ValueError:
        print("Please enter a valid number.")
        return

    print("1. To Do")
    print("2. In Progress")
    print("3. Done")

    statuses = {
        "1": "To Do",
        "2": "In Progress",
        "3": "Done"
    }

    choice = input("Choose new status: ").strip()

    if choice not in statuses:
        print("Invalid status choice.")
        return

    updated = update_task_in_db(task_id, statuses[choice])

    if updated:
        print("Task status updated!")
    else:
        print("Task not found.")


def main():
    create_table()

    while True:
        print("\n===== TaskFlow =====")
        print("1. Add Task")
        print("2. View Tasks")
        print("3. Update Task Status")
        print("4. Exit")

        choice = input("Choose an option: ").strip()

        if choice == "1":
            add_task()
        elif choice == "2":
            view_tasks()
        elif choice == "3":
            update_task_status()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    main()
