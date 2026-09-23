from enum import Enum


class Kind(str, Enum):
    AGENT = "agent"
    SKILL = "skill"
    TOOL = "tool"


class Visibility(str, Enum):
    PUBLIC = "public"
    ORGANIZATION = "organization"
    PRIVATE = "private"


class Status(str, Enum):
    APPROVED = "approved"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"
