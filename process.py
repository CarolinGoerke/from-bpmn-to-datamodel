import xml.etree.ElementTree as ET
from data_classes import Participant, DataObject, DataStore, Task, Message

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

    def get_tasks_and_events_from(self, element):
        return (element.findall('.//bpmn:task', ns) +
            element.findall('.//bpmn:startEvent', ns) +
            element.findall('.//bpmn:intermediateThrowEvent', ns) +
            element.findall('.//bpmn:intermediateCatchEvent', ns) +
            element.findall('.//bpmn:endEvent', ns))
    
    def get_participants(self, root: ET.ElementTree):

        # find all external participants and pools
        participants = root.findall('.//bpmn:participant', ns)
        for p in participants:
            new_participant_intern = p.attrib['processRef'] if 'processRef' in p.attrib else None
            new_participant_name = ("ExtP_" if new_participant_intern is None else "P_") + p.attrib['name'].replace(' ', '_')
            new_participant_id = p.attrib['id']
            self.participants[new_participant_id] = Participant(new_participant_name, new_participant_intern, new_participant_id)

        # find all internal participants represented as lanes
        processes = root.findall('.//bpmn:process', ns)
        for process in processes:
            process_id = process.attrib.get('id')
            pool = next((p for p in self.participants.values() if str(p.intern) == str(process_id)), None)
            participants = process.findall('.//bpmn:lane', ns)
            if (len(participants) > 0):
                for p in participants:
                    new_id = p.attrib['id']
                    new_name = "P_" + p.attrib['name'].replace(' ', '_')
                    self.participants[new_id] = Participant(new_name, process_id, new_id, pool.name)

                    # find all activities that are part of this lane
                    for element in p.iter():
                        element_id = element.text
                        if ('Activity' in element_id or 'Event' in element_id):
                            self.tasks[element_id] = Task(element_id, None, self.participants[new_id], None, None)
            # this is the case if there are no lanes but only one pool
            else:
                tasks = self.get_tasks_and_events_from(process)
                for task in tasks:
                    new_id = task.attrib['id']
                    self.tasks[new_id] = Task(new_id, None, pool, None, None)

    def get_data_objects(self, root: ET.ElementTree):
        all_data_objects = root.findall('.//bpmn:dataObjectReference', ns)
        for o in all_data_objects:
            name = "DO_" + o.attrib['name'].replace(' ', '_')
            o_id = o.attrib['id']
            self.data_objects[o_id] = DataObject(name, o_id)

    def get_data_stores(self, root: ET.ElementTree):
        all_data_stores = root.findall('.//bpmn:dataStoreReference', ns)
        for s in all_data_stores:
            name = "DS_" + s.attrib['name'].replace(' ', '_')
            s_id = s.attrib['id']
            self.data_stores[s_id] = DataStore(name, s_id)

    def get_tasks(self, root: ET.ElementTree):
        all_tasks = self.get_tasks_and_events_from(root)
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
            message_name = None
            if isinstance(source, Task):
                message_name = source.name
            elif isinstance(target, Task):
                message_name = target.name
            self.messages[_id] = Message(_id, message_name, source, target)
