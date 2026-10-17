class ApiError(Exception):
    """An error with an HTTP status code. `detail` is sent to the client as the "detail" field."""

    def __init__(self, status_code: int, detail):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail
