from typing import List, Optional


class APIError(Exception):
    """Custom exception for API errors that standardize to an errors array."""

    def __init__(self, status_code: int, errors: Optional[List[str]] = None, message: Optional[str] = None):
        # Accept old single message too; normalize to list
        if errors is None and message is not None:
            errors = [message]
        self.status_code = status_code
        self.errors = errors or ["An unknown API error occurred."]
        super().__init__(f"API Error {status_code}: {'; '.join(self.errors)}")
