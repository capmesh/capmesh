from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class A2AInterface(BaseModel):
    protocol: Literal["a2a"]
    endpoint: str


class MCPInterface(BaseModel):
    protocol: Literal["mcp"]
    server: str
    tool_name: str | None = None


class SkillInterface(BaseModel):
    protocol: Literal["skill"]
    instructions: str
    assets: list[str] = Field(default_factory=list)


class RESTInterface(BaseModel):
    protocol: Literal["rest"]
    endpoint: str
    auth_type: str
    request_mapping: dict = Field(default_factory=dict)
    response_mapping: dict = Field(default_factory=dict)


Interface = Annotated[
    Union[A2AInterface, MCPInterface, SkillInterface, RESTInterface],
    Field(discriminator="protocol"),
]
