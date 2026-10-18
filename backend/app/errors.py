class MacroError(Exception):
    def __init__(self, message: str, status: int = 409):
        self.message = message
        self.status = status
        super().__init__(message)
