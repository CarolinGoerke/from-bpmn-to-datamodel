from data_classes import Participant

class ClassDiagram:
    def __init__(self):
        self.classes = {}
        self.messageAssociations = {}
        self.dataReadAssociations = []
        self.dataWriteAssociations = []
        self.dataReadWriteAssociations = []

    def association_not_included(self, association):
        return association not in self.dataWriteAssociations and \
                    association not in self.dataReadAssociations and \
                    association not in self.dataReadWriteAssociations

    def get_data_access_edge(self, association, label):
        association = list(association)
        if association[0].startswith('P_') or association[0].startswith('ExtP_'):
            return f"{association[0]} -> {association[1]} [ label=<{label}> taillabel=<*>, headlabel=<*> ]\n"
        else:
            return f"{association[1]} -> {association[0]} [ label=<{label}> taillabel=<*>, headlabel=<*> ]\n"

    def as_dot(self):
        template = r"""digraph G {
            fontname = "Courier"
            fontsize = 8
            rankdir = BT
            # splines=ortho
            # forcelabels=true
            

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
            template += f"{c} [ label=<{{<b>{c}</b><br/>|{'<br/>'.join(self.classes[c].properties)}|<br/>}}> ]\n"

        for me in self.messageAssociations:
            message_names = self.messageAssociations[me]
            if len(message_names) > 1:
                association_name = f"{me[0].name.split('_', 1)[1]}_{me[1].name.split('_', 1)[1]}"
                template += f"{association_name} [ label=<{{&lt;&lt;enumeration&gt;&gt;<br/><b>{association_name}</b><br/>|{'<br/>'.join(message_names)}|<br/>}}> ]\n"

        template += """edge [
            arrowhead="none"
            fontsize = 8
            labeldistance=1
        ]
        """

        for me in self.messageAssociations:
            message_names = self.messageAssociations[me]
            if len(message_names) > 1:
                template += f"{me[0].name} -> {me[1].name} [ label=<{me[0].name.split('_', 1)[1]}-{me[1].name.split('_', 1)[1]}>, taillabel=<*>, headlabel=<*> ]\n"
            else:
                template += f"{me[0].name} -> {me[1].name} [ label=<{message_names[0]}>, taillabel=<*>, headlabel=<*> ]\n"

        template += """edge [
            dir="forward"
            arrowhead="open"
            fontsize=8
            labeldistance=1
        ]
        """

        for assoc in self.dataWriteAssociations:
            template += self.get_data_access_edge(assoc, 'write')

        for assoc in self.dataReadAssociations:
            template += self.get_data_access_edge(assoc, 'read')

        for assoc in self.dataReadWriteAssociations:
            template += self.get_data_access_edge(assoc, 'read and write')

        template += """edge [
            arrowhead="ediamond"
            fontsize = 8
        ]
        """

        for c in self.classes:
            if self.classes[c].parent:
                template += f"{c} -> {self.classes[c].parent}\n"

        template += "}"
        return template