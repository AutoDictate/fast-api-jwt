from fastapi.exceptions import RequestValidationError
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

def add_exception_handlers(app):
    async def validation_exception_handler(request: Request,
                                           exc: RequestValidationError):
        errors = exc.errors()
        messages = errors[0]['msg']
        return JSONResponse( status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"message": messages})
