
import jwt
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Depends,
    status,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr
from pwdlib import PasswordHash

from database import (
    create_table,
    create_users_table,
    create_user,
    get_user_by_email,
    get_all_tasks,
    add_task_to_db,
    update_task_in_db,
    delete_task_from_db,
    get_tasks_by_status,
    search_tasks,
    assign_unowned_tasks_to_existing_user,
)

from security import (
    verify_password,
    create_access_token,
    decode_access_token,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_users_table()
    create_table()
    assign_unowned_tasks_to_existing_user()
    yield


app = FastAPI(
    title="TaskFlow API",
    lifespan=lifespan
)


password_hash = PasswordHash.recommended()


bearer_scheme = HTTPBearer()



def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """Validate the bearer token and return the authenticated user's ID."""
    token = credentials.credentials

    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])

    except (jwt.InvalidTokenError, ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id




class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)



class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@app.get("/")
def home():
    return {
        "message": "Welcome to TaskFlow API",
        "status": "running"
    }




@app.get("/tasks")
def list_tasks(
    search: str | None = Query(default=None, min_length=1, max_length=200),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: int = Depends(get_current_user),
):
    allowed_statuses = {"To Do", "In Progress", "Done"}

    if status_filter is not None and status_filter not in allowed_statuses:
        raise HTTPException(
            status_code=422,
            detail="Invalid status. Use To Do, In Progress, or Done."
        )

    tasks = search_tasks(
    owner_id=user_id,
    search=search.strip() if search else None,
    status=status_filter,
    limit=limit,
    offset=offset,
)

    return [
        {"id": task[0], "title": task[1], "status": task[2]}
        for task in tasks
    ]




@app.post("/tasks", status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    user_id: int = Depends(get_current_user),
):
    title = task.title.strip()

    if not title:
        raise HTTPException(
            status_code=422,
            detail="Task title cannot be empty",
        )

    task_id = add_task_to_db(title, user_id)

    return {
        "id": task_id,
        "title": title,
        "status": "To Do",
    }

class TaskUpdate(BaseModel):
    status: Literal["To Do", "In Progress", "Done"]


@app.patch("/tasks/{task_id}")
def update_task(
    task_id: int,
    task: TaskUpdate,
    user_id: int = Depends(get_current_user),
):
    updated = update_task_in_db(task_id, task.status, user_id)

    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "message": "Task status updated successfully",
        "id": task_id,
        "status": task.status,
    }


@app.delete("/tasks/{task_id}")
def delete_task(
    task_id: int,
    user_id: int = Depends(get_current_user),
):
    deleted = delete_task_from_db(task_id, user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")

    return {
        "message": "Task deleted successfully",
        "id": task_id,
    }


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserRegister):
    email = str(user.email).lower().strip()
    username = user.username.strip()

    if len(username) < 2:
        raise HTTPException(
            status_code=422,
            detail="Username must contain at least 2 non-space characters."
        )

    if get_user_by_email(email):
        raise HTTPException(
            status_code=409,
            detail="Email is already registered."
        )

    hashed_password = password_hash.hash(user.password)

    user_id = create_user(
        username=username,
        email=email,
        hashed_password=hashed_password,
    )

    return {
        "id": user_id,
        "username": username,
        "email": email,
        "message": "User registered successfully.",
    }
    

@app.post("/auth/login")
def login_user(user: UserLogin):
    email = str(user.email).lower().strip()
    existing_user = get_user_by_email(email)

    if not existing_user or not verify_password(
        user.password,
        existing_user[3],
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(existing_user[0])

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

