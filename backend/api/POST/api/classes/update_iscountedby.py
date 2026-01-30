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


@router.post("/api/classes/update_iscountedby")
def update_iscountedby(data: ClassUpdateIsCountedByRequest, request: Request, user_info=Depends(get_current_user_info)):

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

    class_name_to_update = data.class_
    day_identifier = data.dayIdentifier
    new_value = data.value

    if day_identifier not in ['1', '2', '3']:
        raise HTTPException(status_code=400, detail="Invalid dayIdentifier. Must be '1', '2', or '3'.")

    field_to_update = f"iscountedby{day_identifier}"

    # Check config
    allow_self_count_str = 'true'
    config_file_path = DATA_DIR / 'config.json'
    try:
        if config_file_path.is_file():
            with open(config_file_path, 'r', encoding='utf-8') as f:
                current_config_on_disk = json.load(f)
            allow_self_count_str = current_config_on_disk.get('can_students_count_their_own_class', 'true')
    except:
        pass

    allow_self_count = allow_self_count_str.lower() == 'true'

    if not allow_self_count and new_value == class_name_to_update:
        raise HTTPException(status_code=400, detail=f"Configuration prevents class '{class_name_to_update}' from counting itself.")

    with data_lock:
        class_found = False
        for cls_item in class_data_store:
            if cls_item['class'] == class_name_to_update:
                cls_item[field_to_update] = new_value
                class_found = True
                break

        if not class_found:
             raise HTTPException(status_code=404, detail=f"Class '{class_name_to_update}' not found.")

        if save_class_data_to_db():
            return {"success": True, "message": f"Assignment for class '{class_name_to_update}' on day {day_identifier} updated to '{new_value}' and saved."}
        else:
             raise HTTPException(status_code=500, detail=f"Assignment for class '{class_name_to_update}' updated in memory, but FAILED to save to file.")
