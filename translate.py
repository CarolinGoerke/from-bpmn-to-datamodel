import subprocess
import sys
from class_diagram import ClassDiagram
from process import Process
from data_classes import Participant, Class_Diagram_Class

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


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 translate.py [output_filename] [input]")
        sys.exit(2)
    
    diagram = ClassDiagram()
    classes = []
    messageAssociations = []
    tasks = []
    for i in range(2, len(sys.argv)):
        process = Process(sys.argv[i])
        classes += list(process.data_stores.values()) + list(process.data_objects.values()) + list(process.participants.values())
        messageAssociations += list(process.messages.values())
        tasks += list(process.tasks.values())


    class_diagram_classes = {}
    for obj in classes:
        if obj.name not in class_diagram_classes:
            if hasattr(obj, 'pool'):
                new_class = Class_Diagram_Class(obj.name, { obj._id }, obj.properties, obj.pool)
            else:
                new_class = Class_Diagram_Class(obj.name, { obj._id }, obj.properties, None)
            class_diagram_classes[obj.name] = new_class
        else:
            class_diagram_classes[obj.name].ids.add(obj._id)
            class_diagram_classes[obj.name].properties |= obj.properties
            if hasattr(obj, 'pool') and class_diagram_classes[obj.name].parent is None:
                class_diagram_classes[obj.name].parent = obj.pool

    diagram.classes = class_diagram_classes

    for obj in messageAssociations:
        # avoid having multiple Associations between the same two classes
        message = set((
            obj.source if isinstance(obj.source, Participant) else obj.source.participant, 
            obj.target if isinstance(obj.target, Participant) else obj.target.participant))
        message = tuple(message)
        if (message not in diagram.messageAssociations):
            diagram.messageAssociations[message] = [ obj.name ]
        else:
            if obj.name not in diagram.messageAssociations[message]:
                diagram.messageAssociations[message].append(obj.name)

    for task in tasks:
        inputs = task.data_in
        outputs = task.data_out
        associatedData = inputs + outputs
        if associatedData:
            for do in inputs:
                dataReadAssociation = set((task.participant.name, do.name))
                if (dataReadAssociation in diagram.dataWriteAssociations):
                    diagram.dataReadWriteAssociations.append(dataReadAssociation)
                    diagram.dataWriteAssociations.remove(dataReadAssociation)
                elif (diagram.association_not_included(dataReadAssociation)):
                    diagram.dataReadAssociations.append(dataReadAssociation)

            for do in outputs:
                dataWriteAssociation = set((task.participant.name, do.name))
                if (dataWriteAssociation in diagram.dataReadAssociations):
                    diagram.dataReadWriteAssociations.append(dataWriteAssociation)
                    diagram.dataReadAssociations.remove(dataWriteAssociation)
                elif (diagram.association_not_included(dataWriteAssociation)):
                    diagram.dataWriteAssociations.append(dataWriteAssociation)
        
        if inputs and outputs:
            for do_in in inputs:
                for do_out in outputs:
                    if do_in.name != do_out.name:
                        data_association = set((do_in, do_out))
                        diagram.data_associations.append(data_association)
                
    
    dot2png(diagram.as_dot(), replace_extension(sys.argv[1], "png"))

if __name__ == "__main__":
    main()
