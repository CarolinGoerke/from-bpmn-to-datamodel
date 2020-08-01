import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
import subprocess
import sys
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

ns = {'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL'}

class Process:
    def __init__(self, filename):
        tree = ET.parse(filename)
        root = tree.getroot()
        
        self.participants = {}
        self.data_objects = {}
        self.data_stores = {}
        self.messages = {}
        self.tasks = {}

        self.get_participants(root)
        self.get_data_objects(root)
        self.get_data_stores(root)
        self.get_tasks(root)
        self.get_messages(root)

        self.identify_atrributes()

    def identify_atrributes(self):
        for message in self.messages.values():
            if isinstance(message.source, Task) and isinstance(message.target, Participant):
                for obj in message.source.data_in + message.source.data_out:
                    obj.properties.add(message.target.name)
            elif isinstance(message.source, Participant) and isinstance(message.target, Task):
                for obj in message.target.data_out:
                    obj.properties.add(message.source.name)
            else:
                print("Ignoring message from Task to Task or Participant to Participant.")


    
    def get_participants(self, root: ET.ElementTree):

        # find all external participants and pools
        participants = root.findall('.//bpmn:participant', ns)
        for p in participants:
            new_participant_intern = p.attrib['processRef'] if 'processRef' in p.attrib else None
            new_participant_name = ("P_" if new_participant_intern is None else "ExtP_") + p.attrib['name']
            new_participant_id = p.attrib['id']
            self.participants[new_participant_id] = Participant(new_participant_name, new_participant_intern, new_participant_id)

        # find all internal participants represented as lanes
        processes = root.findall('.//bpmn:process', ns)
        for process in processes:
            participants = process.findall('.//bpmn:lane', ns)
            if (len(participants) > 0):
                for p in participants:
                    new_id = p.attrib['id']
                    new_name = "P_" + p.attrib['name']
                    self.participants[new_id] = Participant(new_name, process.attrib.get("id"), new_id, process.attrib.get("id"))

                    # find all activities that are part of this lane
                    for element in p.iter():
                        if ('Activity' in element.text):
                            self.tasks[element.text] = Task(element.text, None, self.participants[new_id], None, None)
            # this is the case if there are no lanes but only one pool
            else:
                participant = None
                for p in self.participants.values():
                    if str(p.intern) == str(process.attrib['id']):
                        participant = p
                
                tasks = process.findall('.//bpmn:task', ns) + process.findall('.//bpmn:startEvent', ns) + process.findall('.//bpmn:intermediateThrowEvent', ns) + process.findall('.//bpmn:intermediateCatchEvent', ns) 
                for task in tasks:
                    new_id = task.attrib['id']
                    self.tasks[new_id] = Task(new_id, None, participant, None, None)
            
    def get_data_objects(self, root: ET.ElementTree):
        all_data_objects = root.findall('.//bpmn:dataObjectReference', ns)
        for o in all_data_objects:
            name = "DO_" + o.attrib['name']
            o_id = o.attrib['id']
            self.data_objects[o_id] = DataObject(name, o_id)

    def get_data_stores(self, root: ET.ElementTree):
        all_data_stores = root.findall('.//bpmn:dataStoreReference', ns)
        for s in all_data_stores:
            name = "DS_" + s.attrib['name']
            s_id = s.attrib['id']
            self.data_stores[s_id] = DataStore(name, s_id)

    def get_tasks(self, root: ET.ElementTree):
        all_tasks = root.findall('.//bpmn:task', ns) + root.findall('.//bpmn:startEvent', ns) + root.findall('.//bpmn:intermediateThrowEvent', ns) + root.findall('.//bpmn:intermediateCatchEvent', ns) 
        for t in all_tasks:
            _id = t.attrib['id']
            name = t.attrib['name'] if 'name' in t.attrib else f"{_id}"
            participant = self.tasks[_id].participant
            data_out = t.findall('.//bpmn:dataOutputAssociation', ns)
            data_in = t.findall('.//bpmn:dataInputAssociation', ns)

            target_objects = []
            if len(data_out) >= 1:
                for data in data_out:
                    target_id = data.findall('.//bpmn:targetRef', ns)[0].text
                    target_object = self.data_objects.get(target_id, self.data_stores.get(target_id))
                    assert target_object is not None, "targetRef references non existing data object: " + target_id
                    target_objects.append(target_object)
            
            source_objects = []
            if len(data_in) >= 1:
                for data in data_in:
                    source_id = data.findall('.//bpmn:sourceRef', ns)[0].text
                    source_object = self.data_objects.get(source_id, self.data_stores.get(source_id))
                    assert source_object is not None, "sourceRef references non existing data object"
                    # we probably need to check whether the data object/store is already in there
                    source_objects.append(source_object)

            self.tasks[_id] = Task(_id, name, participant, target_objects, source_objects)


    def get_messages(self, root: ET.ElementTree):
        all_messages = root.findall('.//bpmn:messageFlow', ns)
        for m in all_messages:
            _id = m.attrib['id']
            source_id = m.attrib['sourceRef']
            source = self.tasks.get(source_id, self.participants.get(source_id))
            target_id = m.attrib['targetRef']
            target = self.tasks.get(target_id, self.participants.get(target_id))
            assert source is not None, "Found message with undefined source"
            assert target is not None, "Found message with undefined target"
            self.messages[_id] = Message(_id, source, target)

    # naming is a little unlucky, this always returns a participant for the message
    def get_participant_from_id(self, id):
        if ('Activity' in id):
            return self.tasks[id].participant
        elif ('Participant' in id):
            return self.participants[id]


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
        self.classes = []
        self.messageAssociations = []
        self.dataReadAssociations = []
        self.dataWriteAssociations = []
        self.dataReadWriteAssociations = []

    def associationNotIncluded(self, association):
        return association not in self.dataWriteAssociations and \
                    association not in self.dataReadAssociations and \
                    association not in self.dataReadWriteAssociations

    def getTemplateForDataAccessEdge(self, association, label):
        association = list(association)
        if 'Data' in association[0]._id:
            return f"{association[1]._id} -> {association[0]._id} [ label=<{label}> ]\n"
        else:
            return f"{association[0]._id} -> {association[1]._id} [ label=<{label}> ]\n"

    def as_dot(self):
        template = r"""digraph G {
            fontname = "Courier"
            fontsize = 8
            rankdir = BT

            node [
                fontname = "Courier"
                fontsize = 8
                shape = "record"
            ]

            edge [
                arrowhead="none"
                fontsize = 8
            ]
        """
        for c in self.classes:
            template += f"{c._id} [ label=<{{<b>{c.name}</b><br/>|{'<br/>'.join(c.properties)}|<br/>}}> ]\n"

        template += """edge [
            arrowhead="none"
            fontsize = 8
        ]
        """

        for me in self.messageAssociations:
            message = list(me)
            template += f"{message[0]._id} -> {message[1]._id}\n"
        
        template += """edge [
            dir="forward"
            arrowhead="open"
            fontsize = 8
        ]
        """

        for assoc in self.dataWriteAssociations:
            template += self.getTemplateForDataAccessEdge(assoc, 'write')

        for assoc in self.dataReadAssociations:
            template += self.getTemplateForDataAccessEdge(assoc, 'read')

        for assoc in self.dataReadWriteAssociations:
            template += self.getTemplateForDataAccessEdge(assoc, 'read and write')

        template += """edge [
            arrowhead="empty"
            fontsize = 8
        ]
        """
        for participant1 in self.classes:
            if not isinstance(participant1, Participant):
                continue
            for participant2 in self.classes:
                if not isinstance(participant2, Participant):
                    continue
                if participant1._id == participant2._id:
                    continue
                if participant1.is_intern and participant2.is_intern:
                    if participant1.intern == participant2.pool and participant2.pool is not None and participant1.pool is None:
                        template += f"{participant2._id} -> {participant1._id}\n"



        template += "}"
        return template

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 translate.py [input]")
        sys.exit(2)
    process = Process(sys.argv[1])
    diagram = ClassDiagram()
    classes = list(process.data_stores.values()) + list(process.data_objects.values()) + list(process.participants.values())
    messageAssociations = list(process.messages.values())

    for obj in classes:
        diagram.classes.append(obj)

    for obj in messageAssociations:
        # avoid having multiple Associations between the same two classes
        message = set((
            obj.source if isinstance(obj.source, Participant) else obj.source.participant, 
            obj.target if isinstance(obj.target, Participant) else obj.target.participant))
        if (message not in diagram.messageAssociations):
            diagram.messageAssociations.append(message)

    for task in list(process.tasks.values()):
        associatedData = task.data_in + task.data_out
        if associatedData:
            for do in task.data_in:
                dataReadAssociation = set((task.participant, do))
                if (dataReadAssociation in diagram.dataWriteAssociations):
                    diagram.dataReadWriteAssociations.append(dataReadAssociation)
                    diagram.dataWriteAssociations.remove(dataReadAssociation)
                elif (diagram.associationNotIncluded(dataReadAssociation)):
                    diagram.dataReadAssociations.append(dataReadAssociation)

            for do in task.data_out:
                dataWriteAssociation = set((task.participant, do))
                if (dataWriteAssociation in diagram.dataReadAssociations):
                    diagram.dataReadWriteAssociations.append(dataWriteAssociation)
                    diagram.dataReadAssociations.remove(dataWriteAssociation)
                elif (diagram.associationNotIncluded(dataWriteAssociation)):
                    diagram.dataWriteAssociations.append(dataWriteAssociation)
    
    dot2png(diagram.as_dot(), replace_extension(sys.argv[1], "png"))

if __name__ == "__main__":
    main()
