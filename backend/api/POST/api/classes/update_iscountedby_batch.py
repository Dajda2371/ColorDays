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


@router.post("/api/classes/update_iscountedby_batch")
def update_iscountedby_batch(data: ClassUpdateIsCountedByBatchRequest, request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info

    # Check session
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie:
        if session_cookie == VALID_SESSION_VALUE:
            is_logged_in = True
        elif session_cookie in active_sessions:
            is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    if user_role not in [ADMIN_ROLE, TEACHER_ROLE]:
         raise HTTPException(status_code=403, detail="Forbidden: Administrator or Teacher access required.")

    updates = data.updates
    if not updates:
        return {"success": True, "message": "No updates provided."}

    # Check config once
    allow_self_count_str = 'true'
    config_file_path = DATA_DIR / 'config.json'
    try:
        if config_file_path.is_file():
            with open(config_file_path, 'r', encoding='utf-8') as f:
                current_config_on_disk = json.load(f)
            allow_self_count_str = current_config_on_disk.get('can_students_count_their_own_class', 'true')
    except:
        pass

    allow_self_count = allow_self_count_str.lower() != 'false'

    with data_lock:
        updated_count = 0
        for update in updates:
            class_name = update.class_
            day_identifier = update.dayIdentifier
            new_value = update.value

            if day_identifier not in ['1', '2', '3']:
                continue

            if not allow_self_count and new_value == class_name:
                continue # Skip invalid self-assignment based on config

            field_to_update = f"iscountedby{day_identifier}"

            for cls_item in class_data_store:
                if cls_item['class'] == class_name:
                    cls_item[field_to_update] = new_value
                    updated_count += 1
                    break

        if updated_count > 0:
            if save_class_data_to_db():
                return {"success": True, "message": f"Updated {updated_count} assignments."}
            else:
                raise HTTPException(status_code=500, detail="Failed to save data.")
        else:
            return {"success": True, "message": "No changes made."}
