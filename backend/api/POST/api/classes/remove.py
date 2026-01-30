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


@router.post("/api/classes/remove")
def remove_class(data: ClassRemoveRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name_to_remove = data.class_

    with data_lock:
        original_len = len(class_data_store)
        new_store = [c for c in class_data_store if c['class'] != class_name_to_remove]

        if len(new_store) < original_len:
            class_data_store[:] = new_store
            if save_class_data_to_db():
                return {"success": True, "message": f"Class '{class_name_to_remove}' removed successfully."}
            else:
                 raise HTTPException(status_code=500, detail=f"Class '{class_name_to_remove}' removed from memory, but FAILED to save to file.")
        else:
             raise HTTPException(status_code=404, detail=f"Class '{class_name_to_remove}' not found.")
