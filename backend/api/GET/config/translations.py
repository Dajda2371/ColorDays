from fastapi import APIRouter, HTTPException, Response
from config import TRANSLATIONS_FILE_PATH

router = APIRouter()

@router.get("/api/translations")
def get_translations():
    if TRANSLATIONS_FILE_PATH.is_file():
        try:
            with open(TRANSLATIONS_FILE_PATH, 'rb') as f:
                content = f.read()
            return Response(content=content, media_type="application/json")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error serving translations file: {e}")
    else:
        raise HTTPException(status_code=404, detail="Translations file not found.")
