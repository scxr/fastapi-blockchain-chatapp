from pydantic import BaseModel
from typing import Optional
from time import time

class Post(BaseModel):
    author: str
    content: str
    timestamp: Optional[float] = time()

class Peer(BaseModel):
    node_address: str

