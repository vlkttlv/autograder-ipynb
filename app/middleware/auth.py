# from fastapi import Request, Response
# import jwt
# from starlette.middleware.base import BaseHTTPMiddleware
# from fastapi.responses import RedirectResponse

# from app.auth.auth import create_access_token
# from app.auth.dependencies import get_current_user, get_current_user, get_refresh_token
# from app.exceptions import IncorrectTokenFormatException, TokenExpiredException, UserIsNotPresentException
# class RefreshTokenMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         # Если пользователь идет на страницы аутентификации, пропускаем проверку токена
#         if request.url.path.startswith("/pages/auth") or request.url.path.startswith("/auth/"):
#             return await call_next(request)

#         try:
#             # Пробуем получить пользователя
#             await get_current_user(request)
#         except (IncorrectTokenFormatException, TokenExpiredException, UserIsNotPresentException):
#             # Ошибка токена - пробуем обновить токен через БД
#             try:
#                 refresh_token = await get_refresh_token(request=request)
#                 payload = jwt.decode(refresh_token, options={"verify_signature": False, "verify_exp": False})
#                 user_id = payload.get("sub")
#                 role = payload.get("role")
#                 if not user_id or not role:
#                     return RedirectResponse(url="/pages/auth/login")

#                 new_access_token = create_access_token({"sub": user_id, "role": role})
                
#                 # Ставим новый токен в куки
#                 response = RedirectResponse(url=request.url.path)
#                 response.set_cookie(key="access_token", value=new_access_token, httponly=True)
#                 return response

#             except Exception as e:
#                 # если рефреш токен тоже битый
#                 return RedirectResponse(url="/pages/auth/login")

#         # Если токен валидный, идем дальше
#         response = await call_next(request)
#         return response
