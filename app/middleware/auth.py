import time
import jwt
import httpx
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.config import settings


class TokenRefreshMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):

        # Если пользователь идет на страницы аутентификации, пропускаем проверку токена
        if request.url.path.startswith("/pages/auth") or request.url.path.startswith("/auth/"):
            return await call_next(request)
        
        access_token = request.cookies.get("access_token")

        if access_token:
            try:
                payload = jwt.decode(access_token, options={"verify_signature": False, "verify_exp": False})
                exp = payload.get("exp")
                now = int(time.time())

                # Если истёк или истечёт через 5 минут
                if exp and exp - now < 300:
                    async with httpx.AsyncClient(base_url=str(request.base_url)) as client:
                        refresh_response = await client.post("/token/refresh", cookies=request.cookies)

                    if refresh_response.status_code == 200:
                        new_access_token = refresh_response.json().get("access_token")
                        if new_access_token:
                            request.cookies["access_token"] = new_access_token
                            response = await call_next(request)
                            response.set_cookie("access_token", new_access_token, httponly=True)
                            return response
                    else:
                        return JSONResponse(status_code=401, content={"detail": "Unable to refresh token"})

            except jwt.InvalidTokenError:
                return JSONResponse(status_code=401, content={"detail": "Invalid access token"})

        # Если access_token отсутствует или валиден — просто продолжаем
        response = await call_next(request)
        return response
