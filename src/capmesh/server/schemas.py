from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str


class RegisterResponse(BaseModel):
    digest: str
    message: str
