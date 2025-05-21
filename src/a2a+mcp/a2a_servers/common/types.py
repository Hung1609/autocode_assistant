# This file is used to:
# model entities(các thực thể) like Task, Message, Artifact, Request/Response RPC, Error to serve an interactive system between users and AI agents via JSON-RPC 2.0 protocol

from typing import Union, Any
from pydantic import BaseModel, Field, TypeAdapter
from typing import Literal, List, Annotated, Optional
from datetime import datetime
from pydantic import model_validator, ConfigDict, field_serializer
from uuid import uuid4
from enum import Enum
from typing_extensions import Self


