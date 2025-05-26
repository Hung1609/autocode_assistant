import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from . import models, schemas
from .database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/tasks", response_model=list[schemas.Task])
def read_tasks(db: Session = Depends(get_db)):
    logger.info(f"Entering read_tasks with args: {locals()}")
    try:
        tasks = db.query(models.Task).all()
        logger.info(f"Exiting read_tasks with result: {tasks}")
        return tasks
    except Exception as e:
        logger.error(f"Error in read_tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/tasks", response_model=schemas.Task, status_code=201)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    logger.info(f"Entering create_task with args: {locals()}")
    try:
        db_task = models.Task(description=task.description)
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        logger.info(f"Exiting create_task with result: {db_task}")
        return db_task
    except Exception as e:
        logger.error(f"Error in create_task: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db)):
    logger.info(f"Entering update_task with args: {locals()}")
    try:
        db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if db_task is None:
            raise HTTPException(status_code=404, detail="Task not found")

        db_task.is_complete = task.is_complete
        db.commit()
        db.refresh(db_task)
        logger.info(f"Exiting update_task with result: {db_task}")
        return db_task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_task: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    logger.info(f"Entering delete_task with args: {locals()}")
    try:
        db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
        if db_task is None:
            raise HTTPException(status_code=404, detail="Task not found")

        db.delete(db_task)
        db.commit()
        logger.info("Exiting delete_task")
        return
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in delete_task: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal Server Error")