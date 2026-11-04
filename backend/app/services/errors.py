"""Domain failures, independent of HTTP; `status_code` is what the API answers for each one."""


class DomainError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class Conflict(DomainError):
    status_code = 409


class InvalidContent(DomainError):
    status_code = 422


class NotFound(DomainError):
    status_code = 404
