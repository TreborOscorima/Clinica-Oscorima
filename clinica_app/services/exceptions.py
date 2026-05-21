class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(ServiceError):
    def __init__(self, message: str = "Recurso no encontrado"):
        super().__init__(message, 404)


class ConflictError(ServiceError):
    def __init__(self, message: str = "Conflicto de datos"):
        super().__init__(message, 409)
