from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional
from config import ADMIN_ROLE
from dependencies import get_current_admin_user
from data_manager import class_data_store, data_lock, save_class_data_to_db

router = APIRouter()

class ClassAddRequest(BaseModel):
    class_: str = Field(..., alias="class")
    teacher: str
    counts1: Optional[str] = 'F'
    counts2: Optional[str] = 'F'
    counts3: Optional[str] = 'F'
    iscountedby1: Optional[str] = '_NULL_'
    iscountedby2: Optional[str] = '_NULL_'
    iscountedby3: Optional[str] = '_NULL_'

@router.post("/api/classes/add")
def add_class(payload: ClassAddRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name = payload.class_
    teacher = payload.teacher
    counts1 = payload.counts1
    counts2 = payload.counts2
    counts3 = payload.counts3

    if counts1 not in ['T', 'F'] or counts2 not in ['T', 'F'] or counts3 not in ['T', 'F']:
         raise HTTPException(status_code=400, detail="Invalid counts values (must be T or F)")

    with data_lock:
        if any(c['class'] == class_name for c in class_data_store):
             raise HTTPException(status_code=409, detail=f"Class '{class_name}' already exists.")
        
        new_class = {
            "class": class_name, "teacher": teacher,
            "counts1": counts1, "counts2": counts2, "counts3": counts3,
            "iscountedby1": payload.iscountedby1, "iscountedby2": payload.iscountedby2,
            "iscountedby3": payload.iscountedby3
        }
        class_data_store.append(new_class)
        class_data_store.sort(key=lambda x: x['class'])
        
        if save_class_data_to_db():
            return {"success": True, "message": f"Class '{class_name}' added successfully."}
        else:
            class_data_store.remove(new_class)
            raise HTTPException(status_code=500, detail=f"Failed to save class '{class_name}' to file.")
