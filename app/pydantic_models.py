from typing import Optional

from pydantic import BaseModel


class AddTask(BaseModel):
    id: int


class GetTask(BaseModel):
    status: Optional[str]
