from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME, DATA_DIR, SESSION_COOKIE_NAME, VALID_SESSION_VALUE
from data_manager import class_data_store, data_lock, save_class_data_to_db, load_class_data_from_db, server_config
from dependencies import get_current_admin_user, get_current_user_info, active_sessions
import json
import requests
import re
import logging


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


class ClassRemoveRequest(BaseModel):
    class_: str = Field(..., alias="class")


class ClassUpdateCountsRequest(BaseModel):
    class_: str = Field(..., alias="class")
    countField: str
    value: str


class ClassUpdateIsCountedByRequest(BaseModel):
    class_: str = Field(..., alias="class")
    dayIdentifier: str
    value: str


class BatchUpdateItem(BaseModel):
    class_: str = Field(..., alias="class")
    dayIdentifier: str
    value: str


class ClassUpdateIsCountedByBatchRequest(BaseModel):
    updates: list[BatchUpdateItem]


@router.post("/api/classes/add")
def add_class(data: ClassAddRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name = data.class_
    teacher = data.teacher
    counts1 = data.counts1
    counts2 = data.counts2
    counts3 = data.counts3

    if counts1 not in ['T', 'F'] or counts2 not in ['T', 'F'] or counts3 not in ['T', 'F']:
        raise HTTPException(status_code=400, detail="Invalid counts values (must be T or F)")

    with data_lock:
        if any(c['class'] == class_name for c in class_data_store):
             raise HTTPException(status_code=409, detail=f"Class '{class_name}' already exists.")

        new_class = {
            "class": class_name, "teacher": teacher,
            "counts1": counts1, "counts2": counts2, "counts3": counts3,
            "iscountedby1": data.iscountedby1, "iscountedby2": data.iscountedby2,
            "iscountedby3": data.iscountedby3
        }
        class_data_store.append(new_class)
        class_data_store.sort(key=lambda x: x['class'])

        if save_class_data_to_db():
            return {"success": True, "message": f"Class '{class_name}' added successfully."}
        else:
             # Try to remove if failed
             try:
                 class_data_store.remove(new_class)
             except ValueError:
                 pass
             raise HTTPException(status_code=500, detail=f"Failed to save class '{class_name}' to file.")
