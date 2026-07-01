class TelegramException(Exception):
    pass


class TelegramMediaGroupHTTPException(TelegramException):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"Message: {self.message} [Code: {self.status_code}]"
