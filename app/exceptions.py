from fastapi import HTTPException, status


class AutograderException(HTTPException):
    status_code = 500
    detail = ""

    def __init__(self):
        super().__init__(status_code=self.status_code, detail=self.detail)


class IncorrectEmailOrPasswordException(AutograderException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверная почта или пароль"


class IncorrectTokenFormatException(AutograderException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Неверный формат токена"


class TokenAbsentException(AutograderException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Токен отсутствует"


class TokenExpiredException(AutograderException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Срок действия токена истек"


class UserIsNotPresentException(AutograderException):
    status_code = status.HTTP_401_UNAUTHORIZED


class UserAlreadyExistsException(AutograderException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Пользователь уже существует"


class IncorrectFormatAssignmentException(AutograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Файл должен быть в формате .ipynb"


class NotFoundSolutionsInAssignmentException(AutograderException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Не найдены решения"


class NotFoundTestsInAssignmentException(AutograderException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Не найдены скрытые тесты"


class IncorrectRoleException(AutograderException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Некорректная роль"


class SyntaxException(AutograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Синтаксическая ошибка"


class AssignmentNotFoundException(AutograderException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Задание не найдено"


class DeadlineException(AutograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Дедлайн сгорел или еще не начался"


class WgongDateException(AutograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Неверная дата"


class SolutionNotFoundException(AutograderException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Решение не найдено"


class EndedAttemptsException(AutograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Попытки закончились"


class DecodingIPYNBException(AutograderException):
    status_code = status.HTTP_400_BAD_REQUEST
    detail = "Ошибка при декодировании файла .ipynb"
