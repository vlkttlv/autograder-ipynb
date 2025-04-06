from fastapi import HTTPException, status


class AuthograderException(HTTPException):
    status_code = 500
    detail = ""

    def __init__(self):
        super().__init__(status_code=self.status_code, detail=self.detail)

class IncorrectEmailOrPasswordException(AuthograderException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверная почта или пароль"

class IncorrectTokenFormatException(AuthograderException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверный формат токена"

class TokenAbsentException(AuthograderException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Токен отсутствует"

class TokenExpiredException(AuthograderException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Срок действия токена истек"
    
class UserIsNotPresentException(AuthograderException):
    status_code = status.HTTP_401_UNAUTHORIZED

class UserAlreadyExistsException(AuthograderException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь уже существует"


class IncorrectFormatAssignmentException(AuthograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Файл должен быть в формате .ipynb"
    

class NotFoundSolutionsInAssignmentException(AuthograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Не найдены решения"

class NotFoundTestsInAssignmentException(AuthograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Не найдены скрытые тесты"

class IncorrectRoleException(AuthograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Некоректная роль"


class SyntaxException(AuthograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Синтаксическая ошибка"