from pydantic import BaseModel


class StoredCreds(BaseModel):
    instance_url: str
    user: str
    token: str
    expires_at: str
