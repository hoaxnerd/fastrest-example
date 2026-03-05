"""Token authentication for the bookstore API."""

from fastrest.authentication import TokenAuthentication

# In-memory token store for demo purposes.
# In production, look up tokens from the database.
TOKEN_STORE = {
    "admin-token-001": {"id": 1, "user_name": "admin", "is_staff": True},
    "user-token-002": {"id": 2, "user_name": "reader", "is_staff": False},
}


class SimpleUser:
    """Minimal user object returned by authentication."""

    def __init__(self, id, user_name, is_staff=False):
        self.id = id
        self.username = user_name
        self.is_staff = is_staff

    def __bool__(self):
        return True


def get_user_by_token(token_key):
    entry = TOKEN_STORE.get(token_key)
    if entry is None:
        return None
    return SimpleUser(**entry)


token_auth = TokenAuthentication(get_user_by_token=get_user_by_token, keyword="Bearer")
