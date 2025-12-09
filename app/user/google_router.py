import os
from fastapi import APIRouter, Depends, Request, HTTPException
from starlette.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.auth import create_access_token, create_refresh_token
from app.auth.dependencies import get_current_user
from app.db import get_db_session
from app.user.schemas import CompleteProfileSchema
from app.user.service import GroupsService, UsersDAO
from app.config import settings


router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_SECRETS_FILE = settings.CLIENT_SECRETS_FILE
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]
REDIRECT_URI = settings.GOOGLE_REDIRECT_URI

state_storage = {}


@router.get("/login")
async def google_login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    state_storage["google_state"] = state
    return RedirectResponse(url=authorization_url)


@router.get("/callback")
async def google_callback(request: Request,
                          session: AsyncSession = Depends(get_db_session)):
    state = state_storage.get("google_state")
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=REDIRECT_URI,
    )
    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    service = build("oauth2", "v2", credentials=credentials)
    user_info = service.userinfo().get().execute()

    email = user_info["email"]
    google_id = user_info["id"]
    first_name = user_info.get("given_name")
    last_name = user_info.get("family_name")

    existing_user = await UsersDAO.find_one_or_none(session=session, email=email)

    # если юзер новый — создаем, но роль и группу не трогаем
    if not existing_user:
        user_id = await UsersDAO.add(
            session=session,
            email=email,
            google_id=google_id,
            first_name=first_name,
            last_name=last_name,
        )
        user_role = None
        group_id = None
    else:
        user_id = existing_user.id
        user_role = existing_user.role
        group_id = existing_user.group_id

    # создаем токены
    access_token = create_access_token(
        {"sub": str(user_id), "role": user_role or "UNKNOWN"}
    )
    refresh_token = await create_refresh_token(
        {"sub": str(user_id), "role": user_role or "UNKNOWN"},
        session
    )

    # сохраняем токен в cookie
    response = RedirectResponse(
        url=(
            "/pages/complete-profile"  # если нет роли или группы, просим дозаполнить
            if not user_role or (user_role == "STUDENT" and not group_id)
            else (
                "/pages/student-home"
                if user_role == "STUDENT"
                else "/pages/tutor-home"
            )
        )
    )
    response.set_cookie("access_token", access_token, httponly=True)
    return response


@router.post("/complete")
async def complete_profile(
    data: CompleteProfileSchema, current_user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    update_data = {"role": data.role}
    if data.role == "STUDENT" and data.group:
        group = await GroupsService.find_one_or_none(session=session, name=data.group)
        if not group:
            group_id = await GroupsService.add(session=session, name=data.group)
        else:
            group_id = group.id
        update_data["group_id"] = group_id

    await UsersDAO.update(session, current_user.id, **update_data)
    return {"message": "Profile updated"}
