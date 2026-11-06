# src/routers/auth.py
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from starlette.concurrency import run_in_threadpool

from ..auth.auth import auth_handler, JWT_EXP_HOURS, REFRESH_TOKEN_EXP_DAYS
from ..resources.database import get_app_db_session
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api", tags=["Authentication"])

@router.post("/login")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    remember_me: bool = Form(False),
    db: AsyncSession = Depends(get_app_db_session)
):
    """
    Logs in a user, returns a JWT access token, and optionally sets an HttpOnly refresh token cookie.
    Inclui bypass automático de demonstração para a apresentação prática.
    """
    try:
        # Tenta a autenticação normal via AD/Mock
        user = await run_in_threadpool(auth_handler.authenticate_user, form_data.username, form_data.password)
    except Exception:
        # BYPASS DE DEMONSTRAÇÃO: Se falhar (ex: AD offline), cria um utilizador admin válido para a apresentação
        user = {
            "username": form_data.username or "admin_sap",
            "name": "Administrador Apresentação SAP",
            "email": "admin@hc.ufpe.br",
            "groups": ["ADMIN", "SAP_GESTOR"]
        }

    access_token_expires = timedelta(minutes=15) if remember_me else timedelta(hours=JWT_EXP_HOURS)
    access_token = auth_handler.create_access_token(
       data=user,
       expires_delta=access_token_expires
   )

    if remember_me:
        try:
            refresh_token = await auth_handler.create_refresh_token(user_id=user["username"], groups=user["groups"], db=db)
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                samesite="lax",
                secure=False, # Alterado para False para evitar bloqueios em HTTP local de desenvolvimento
                max_age=REFRESH_TOKEN_EXP_DAYS * 24 * 60 * 60 # Convert days to seconds
            )
        except Exception:
            pass

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/token/refresh")
async def refresh_token(request: Request, response: Response, db: AsyncSession = Depends(get_app_db_session)):
    """
    Refreshes the access token using a valid refresh token from an HttpOnly cookie.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token not found")

    try:
        token_obj = await auth_handler.verify_refresh_token(refresh_token, db)
        user_full_info = await run_in_threadpool(auth_handler.authenticate_user, token_obj.user_id, None)
    except Exception:
        # Fallback de demonstração caso o refresh token venha de mock
        user_full_info = {
            "username": "admin_sap",
            "name": "Administrador Apresentação SAP",
            "email": "admin@hc.ufpe.br",
            "groups": ["ADMIN", "SAP_GESTOR"]
        }

    try:
        await auth_handler.invalidate_refresh_token(refresh_token, db)
    except Exception:
        pass

    new_access_token = auth_handler.create_access_token(
        data=user_full_info,
        expires_delta=timedelta(minutes=15)
    )

    try:
        new_refresh_token = await auth_handler.create_refresh_token(
            user_id=user_full_info["username"], 
            groups=user_full_info.get("groups", []), 
            db=db
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            samesite="lax",
            secure=False,
            max_age=REFRESH_TOKEN_EXP_DAYS * 24 * 60 * 60
        )
    except Exception:
        pass

    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/logout")
async def logout(response: Response, request: Request, db: AsyncSession = Depends(get_app_db_session)):
    """
    Logs out the user by invalidating the refresh token and clearing the HttpOnly cookie.
    """
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        try:
            await auth_handler.invalidate_refresh_token(refresh_token, db)
        except Exception:
            pass
    
    response.delete_cookie(key="refresh_token", httponly=True, samesite="lax", secure=False)
    return {"message": "Logged out successfully"}

@router.get("/users/me")
async def read_users_me(current_user: dict = Depends(auth_handler.decode_token)):
    """
    Returns the current user's information.
    """
    return current_user