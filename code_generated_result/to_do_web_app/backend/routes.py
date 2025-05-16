from fastapi import APIRouter, HTTPException, Depends
from typing import List
from .models import Task
from .database import get_db, Session
from pydantic import BaseModel

router = APIRouter()

class TaskCreate(BaseModel):
    description: str

class TaskUpdate(BaseModel):
    is_complete: bool

@router.get("/tasks", response_model=List[Task])
def read_tasks(db: Session = Depends(get_db)):
    """
    Retrieves all to-do tasks.
    """
    tasks = db.query(Task).all()
    return tasks

@router.post("/tasks", response_model=Task, status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """
    Creates a new to-do task.
    """
    db_task = Task(description=task.description)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Deletes a to-do task.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
    return

@router.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    """
    Updates a to-do task (e.g., to mark as complete).
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    task.is_complete = task_update.is_complete
    db.commit()
    db.refresh(task)
    return task