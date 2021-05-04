from fastapi import APIRouter
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from ..auth.authentication import Authentication
from ..globals.authentication import get_authentication

router = APIRouter()


@router.post("/token")
async def login(login_form_data: OAuth2PasswordRequestForm = Depends(),
                auth: Authentication = Depends(get_authentication)):
    try:
        token = auth.login(login_form_data.username, login_form_data.password)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return token

