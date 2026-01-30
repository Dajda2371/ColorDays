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


@router.post("/api/classes/update_counts")
def update_counts(data: ClassUpdateCountsRequest, admin_user: dict = Depends(get_current_admin_user)):
    class_name = data.class_
    count_field = data.countField
    new_value = data.value

    valid_count_fields = ["counts1", "counts2", "counts3"]
    if count_field not in valid_count_fields:
        raise HTTPException(status_code=400, detail=f"Invalid countField. Must be one of {valid_count_fields}")

    if new_value not in ['T', 'F']:
        raise HTTPException(status_code=400, detail="Invalid value. Must be 'T' or 'F'")

    with data_lock:
        class_to_update = next((cls_item for cls_item in class_data_store if cls_item['class'] == class_name), None)

        if not class_to_update:
             raise HTTPException(status_code=404, detail=f"Class '{class_name}' not found.")

        class_to_update[count_field] = new_value
        if save_class_data_to_db():
            return {"success": True, "message": f"Count '{count_field}' for class '{class_name}' updated to '{new_value}'."}
        else:
             raise HTTPException(status_code=500, detail=f"Count for class '{class_name}' updated in memory, but FAILED to save to file.")
