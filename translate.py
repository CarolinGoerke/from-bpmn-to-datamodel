import xml.etree.ElementTree as ET
from dataclasses import dataclass
import subprocess
import sys
from typing import Union, Optional

@dataclass
class Participant:
    name: str
    intern: bool
    _id: str

@dataclass
class DataObject:
    name: str
    _id: str

@dataclass
class DataStore:
    name: str
    _id: str
        
@dataclass
class Task:
    _id: str
    name: str
    data_out: Optional[Union[DataObject, DataStore]]
    data_in: Optional[Union[DataObject, DataStore]]

@dataclass
class Message:
    _id: str
    source: Union[Task, Participant]
    target: Union[Task, Participant]
        

ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}

class Process:
    def __init__(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        
        self.participants={}
        self.data_objects={}
        self.data_stores={}
        self.messages={}
        self.tasks={}

        self.get_participants(root)
        self.get_data_objects(root)
        self.get_data_stores(root)
        self.get_tasks(root)
        self.get_messages(root)
        


    def get_participants(self, root: ET.ElementTree):
        all_participants = root.findall('.//bpmn:participant',ns)
        for p in all_participants:
            new_participant_name = p.attrib['name']
            new_participant_intern = 'processRef' in p.attrib
            new_participant_id = p.attrib['id']
            self.participants[new_participant_id] = Participant(new_participant_name, new_participant_intern, new_participant_id)

    def get_data_objects(self, root: ET.ElementTree):
        all_data_objects = root.findall('.//bpmn:dataObjectReference', ns)
        for o in all_data_objects:
            name = o.attrib['name']
            o_id = o.attrib['id']
            self.data_objects[o_id] = DataObject(name, o_id)

    def get_data_stores(self, root: ET.ElementTree):
        all_data_stores = root.findall('.//bpmn:dataStoreReference', ns)
        for s in all_data_stores:
            name = s.attrib['name']
            s_id = s.attrib['id']
            self.data_stores[s_id] = DataStore(name, s_id)

    def get_messages(self, root: ET.ElementTree):
        all_messages = root.findall('.//bpmn:messageFlow', ns)
        for m in all_messages:
            _id = m.attrib['id']
            source_id = m.attrib['sourceRef']
            target_id = m.attrib['targetRef']
            source = self.tasks.get(source_id, self.participants.get(source_id))
            target = self.tasks.get(target_id, self.participants.get(target_id))
            assert source is not None, "Found message with undefined source"
            assert target is not None, "Found message with undefined target"
            self.messages[_id] = Message(_id, source, target)

    def get_tasks(self, root: ET.ElementTree):
        all_tasks = root.findall('.//bpmn:task', ns)
        for t in all_tasks:
            _id = t.attrib['id']
            name = t.attrib['name']
            data_out = t.findall('.//bpmn:dataOutputAssociation', ns)
            assert len(data_out) <= 1, 'Multiple Outputs'
            data_in = t.findall('.//bpmn:dataInputAssociation', ns)
            assert len(data_in) <= 1, 'Multiple Inputs'

            target_object = None
            if len(data_out) == 1:
                target_id = data_out[0].findall('.//bpmn:targetRef', ns)[0].text
                target_object = self.data_objects.get(target_id, self.data_stores.get(target_id))
                assert target_object is not None, "targetRef references non existing data object: " + target_id
            
            source_object = None
            if len(data_in) == 1:
                source_id = data_in[0].findall('.//bpmn:sourceRef', ns)[0].text
                source_object = self.data_objects.get(source_id, self.data_stores.get(source_id))
                assert source_object is not None, "sourceRef references non existing data object"

            self.tasks[_id] = Task(_id, name, target_object, source_object)

def replace_extension(f: str, new_extension: str):
    point_pos  = f.rfind(".")
    if point_pos == -1:
        return f"{f}.{new_extension}"
    return f"{f[:point_pos]}.{new_extension}"

def dot2png(dot: str, outputfile: str):
    with open(replace_extension(outputfile, "dot"), "w") as file_handle:
        file_handle.write(dot)
        
    with open(outputfile, "wb") as file_handle:
        try:
            subprocess.run(["dot", "-Tpng" , "-Gdpi=150"], input=dot.encode(), stdout=file_handle)
        except FileNotFoundError:
            print("Please install graphviz (brew install graphviz / apt-get install graphviz)")
            print("and make sure that 'dot' is available in your environment path.")

class ClassDiagram:
    def __init__(self):
        self.classes=[]
    
    def as_dot(self):
        template = r"""digraph G {
fontname = "Bitstream Vera Sans"
fontsize = 8
rankdir = BT

node [
    fontname = "Bitstream Vera Sans"
    fontsize = 8
    shape = "record"
]

edge [
    arrowhead="none"
    fontsize = 8
]
"""
        for c in self.classes:
            template += f"{c._id} [ label=<{{<b>{c.name}</b><br/>|<br/>}}> ]\n"
        
        template += "}"
        return template

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 translate.py [input]")
        sys.exit(2)
    process = Process(sys.argv[1])
    diagram = ClassDiagram()
    sources = list(process.data_stores.values()) + list(process.data_objects.values()) + list(process.participants.values())
    for obj in sources:
        diagram.classes.append(obj)
    
    dot2png(diagram.as_dot(), replace_extension(sys.argv[1], "png"))

if __name__ == "__main__":
    main()
