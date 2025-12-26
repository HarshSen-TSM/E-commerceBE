# Utils/logging_filter.py

from utils.request_context import get_current_user


class UserContextFilter:
    def filter(self, record):
        user = get_current_user()

        if user:
            record.user = getattr(user, "email", "unknown")
        else:
            record.user = "anonymous"

        return True
