from fastapi import APIRouter, HTTPException, Response, Body
from pydantic import BaseModel
from config import LANGUAGE_COOKIE_NAME

router = APIRouter()

class LanguageSetRequest(BaseModel):
    language: str

@router.post("/api/language/set")
def set_language(response: Response, payload: LanguageSetRequest):
    code = payload.language
    if code not in ['cs', 'en']:
        raise HTTPException(status_code=400, detail="Invalid language code. Must be 'cs' or 'en'.")
        
    max_age_1_year = 365 * 24 * 60 * 60
    response.set_cookie(key=LANGUAGE_COOKIE_NAME, value=code, path='/', max_age=max_age_1_year, httponly=False)
    
    return {"success": True, "message": f"Language set to {code}"}
