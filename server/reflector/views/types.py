from pydantic import BaseModel


class DeletionStatus(BaseModel):
    status: str
