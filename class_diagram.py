from data_classes import Participant

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