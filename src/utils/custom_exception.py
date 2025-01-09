from http import HTTPStatus

from fastapi import HTTPException


# custom exception class
class CustomHTTPException(HTTPException):
    def __init__(self, status_code: int, message: str):
        super().__init__(status_code=status_code)
        self.message = message
        self.error = HTTPStatus(status_code).phrase
