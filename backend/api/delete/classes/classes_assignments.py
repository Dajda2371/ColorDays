from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional
from config import ADMIN_ROLE, TEACHER_ROLE, SQL_AUTH_USER_STUDENT_COOKIE_NAME, DATA_DIR, SESSION_COOKIE_NAME, VALID_SESSION_VALUE
from data_manager import class_data_store, data_lock, save_class_data_to_db, load_class_data_from_db, server_config, students_data_store, save_students_data_to_db
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


@router.delete("/api/classes/assignments")
def clear_all_assignments(request: Request, user_info=Depends(get_current_user_info)):
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

    with data_lock:
        updated_count = 0
        for cls_item in class_data_store:
            # Check if any value is actually being cleared (optimization)
            if (cls_item.get('iscountedby1') != '_NULL_' or
                cls_item.get('iscountedby2') != '_NULL_' or
                cls_item.get('iscountedby3') != '_NULL_'):

                cls_item['iscountedby1'] = '_NULL_'
                cls_item['iscountedby2'] = '_NULL_'
                cls_item['iscountedby3'] = '_NULL_'
                updated_count += 1

        if updated_count > 0:
            if save_class_data_to_db():
                # Also reset all student assignments since no class counts anyone
                students_modified = False
                for student in students_data_store:
                    if student.get('counts_classes') != '[]':
                        student['counts_classes'] = '[]'
                        students_modified = True
                
                if students_modified:
                    save_students_data_to_db()

                return {"success": True, "message": f"Cleared assignments for {updated_count} classes."}
            else:
                raise HTTPException(status_code=500, detail="Failed to save data.")
        else:
            return {"success": True, "message": "No assignments to clear."}
