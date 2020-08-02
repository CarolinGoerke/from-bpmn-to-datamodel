from dataclasses import dataclass, field
from typing import Union, Optional, List, Set

@dataclass
class Participant:
    name: str
    intern: str
    _id: str
    pool: Optional[str] = None
    properties: Set[str] = field(default_factory=set)

    def __hash__(self):
        return hash(self._id)
    
    @property
    def is_intern(self):
        return self.intern is not None
    
    @property
    def is_extern(self):
        return not self.is_intern

@dataclass
class DataObject:
    name: str
    _id: str
    properties: Set[str] = field(default_factory=set)

    def __hash__(self):
        return hash(self._id)

@dataclass
class DataStore:
    name: str
    _id: str
    properties: Set[str] = field(default_factory=set)

    def __hash__(self):
        return hash(self._id)
        
@dataclass
class Task:
    _id: str
    name: str
    participant: Participant
    data_out: List[Union[DataObject, DataStore]]
    data_in: List[Union[DataObject, DataStore]]

    def __hash__(self):
        return hash(self._id)

@dataclass
class Message:
    _id: str
    source: Union[Task, Participant]
    target: Union[Task, Participant]