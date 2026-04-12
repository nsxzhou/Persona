from __future__ import annotations


class DomainError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class BadRequestError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__(400, detail)


class UnauthorizedError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__(401, detail)


class ForbiddenError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__(403, detail)


class NotFoundError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__(404, detail)


class ConflictError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__(409, detail)


class UnprocessableEntityError(DomainError):
    def __init__(self, detail: str) -> None:
        super().__init__(422, detail)
