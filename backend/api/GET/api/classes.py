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


@router.get("/api/classes")
def list_classes(request: Request, user_info=Depends(get_current_user_info)):
    user_key, user_role = user_info
    student_cookie = request.cookies.get(SQL_AUTH_USER_STUDENT_COOKIE_NAME)

    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    is_logged_in = False
    if session_cookie:
        if session_cookie == VALID_SESSION_VALUE:
            is_logged_in = True
        elif session_cookie in active_sessions:
            is_logged_in = True

    if not is_logged_in:
        raise HTTPException(status_code=401, detail="Authentication required")

    if not (user_role in [ADMIN_ROLE, TEACHER_ROLE] or student_cookie):
        raise HTTPException(status_code=403, detail="Forbidden: Access to this resource is restricted for your account type.")

    with data_lock:
        return class_data_store
