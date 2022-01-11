import datetime
from typing import Any, Callable, Dict, List, OrderedDict, Set, Tuple

from flaskapp.models import ProposalComments, Arguments
from flaskapp.utils.NodeData import NodeData
from flaskapp.utils.df_utils import ARGS_TO_ENTITIES, ENGINE, PROPS_TO_CONTROVERSY

MAX_ENTITIES_IN_STATS = 3
MAX_ASPECTS_IN_STATS = 3
MAX_POPULAR_COMMENTS = 2
MAX_ARGS_STATS_PER_QUERY = 3
DONT_BOTHER_ABOUT_PROPOSAL = -1


ALL_IDS_TO_COMMENTS = dict()
for p in ENGINE.execute("SELECT proposal_comments.id AS proposal_comments_id, proposal_comments.parentid AS proposal_comments_parentid, proposal_comments.proposalid AS proposal_comments_proposalid, proposal_comments.page AS proposal_comments_page, proposal_comments.userid AS proposal_comments_userid, proposal_comments.username AS proposal_comments_username, proposal_comments.usertype AS proposal_comments_usertype, proposal_comments.date AS proposal_comments_date, proposal_comments.time AS proposal_comments_time, proposal_comments.text AS proposal_comments_text, proposal_comments.numvotes AS proposal_comments_numvotes, proposal_comments.numpositivevotes AS proposal_comments_numpositivevotes, proposal_comments.numnegativevotes AS proposal_comments_numnegativevotes FROM proposal_comments;").fetchall():
    c = NodeData(p, "LEGACY_ROW")
    ALL_IDS_TO_COMMENTS[c.id] = c


def controversia_comentario(data: NodeData):
    return data.numvotes/(abs(data.numpositivevotes - data.numnegativevotes) + 1)


def sorter(order_by):
    def sorteador(v: Node):
        if v.data is None:
            return v.id
        if "ordencontroversia" in order_by and v.TYPE == "C":
            return controversia_comentario(v.data)
        elif "ordenvotos" in order_by and v.TYPE == "C":
            return v.data.numpositivevotes - v.data.numnegativevotes
        # NOT IMPLEMENTED WARNING?
        return v.id
    return sorteador


class Node():

    def get_more_whatever(self, tipo: str, limit: int, measure_on_node: Callable, on_list: list, filter: Callable = lambda c: True, mlevel=0, neutral_measure=lambda t: 0):
        return [s.print_tree(type=tipo, notoverridesid=True, max_level=mlevel) for s in sorted([c for c in on_list],
                                                                                               key=lambda com: sum(
            map(
                measure_on_node if (com.TYPE == tipo or tipo == "ALL") else neutral_measure, com.getAllNodesHaving(
                    filter, com.proposalid, type=tipo) or ()
            )
        ),
            reverse=True
        )[0:limit]]

    def __init__(self, data: Any, sid: str = None, id: int = -1, parent=None, children: List = None, type="C", proposalid=-1, ignored=False) -> None:
        self.parent: Node = parent
        self.children: List[Node] = children or []
        self.sid: str = sid or None
        self.data: NodeData = NodeData(
            data) if data is not None and data.__getattribute__('tipo') is None else data
        self.id: int = id or None
        self.TYPE = type
        self.proposals: OrderedDict[int, Node] = None
        self.proposalid = proposalid
        self.ignored = ignored

        if type == "ROOT":
            self.proposals = OrderedDict((c.id, c) for c in children)

    def isroot(self):
        return self.TYPE == "ROOT"

    def getNodeById(self, id: int, proposalid: int, type="C"):
        return self.getNodeHaving(lambda n: n.id == id, proposalid, type)

    def containsId(self, id: int, proposalid: int, type="C"):
        return self.getNodeById(id, proposalid, type) is not None

    def containsData(self, data: Any, type="C"):
        return self.getNodeById(data.id, data.proposalid, type) is not None

    def getNodeBySid(self, sid: str):
        if self.TYPE == sid[0] and self.sid == sid[1:]:
            return self
        else:
            for c in self.children:
                nod = c.getNodeBySid(sid)
                if nod is not None:
                    return nod
        return None

    def link_data(self, type: str, comment: Any, allcomments: Dict[int, Any]):

        def getParent(comentario: Any, tipo_son) -> Tuple[int, Node]:
            if tipo_son == "C":
                if comentario.parentid == -1:
                    parent: Node = self.getNodeById(
                        comentario.proposalid, comentario.proposalid, type="P")
                    pid: int = comentario.proposalid
                else:
                    parent: Node = self.getNodeById(
                        comentario.parentid, comentario.proposalid, type="C")
                    pid: int = comentario.parentid

            elif tipo_son == "A":
                if comentario.commentid == -1:
                    # Caso base A1: argumento es hijo directo de PROPUESTA
                    parent: Node = self.getNodeById(
                        comentario.proposalid, comentario.proposalid, type="P")
                    pid = comentario.proposalid
                else:
                    # Caso base A2: argumento es hijo directo de COMENTARIO
                    parent: Node = self.getNodeById(
                        comentario.commentid, comentario.proposalid, type="C")
                    pid: int = comentario.commentid
            return pid, parent
        inserted = set()

        pid, parent = getParent(comentario=comment, tipo_son=type)
        nuevoNodo = Node(data=comment,
                         sid=None,
                         id=comment.id,
                         parent=None,
                         children=list(), type=type, proposalid=comment.proposalid)
        inserted.add(comment.id)
        while parent is None:
            # RECURSION: padre/s no existe/n, hay que crearlos y sabemos que son nodos comentarios:
            # este es el dato del padre si también pasó el filtro
            comment: ProposalComments = allcomments.get(pid)
            # Esto pasa si el padre no pasó el filtro. En este caso, hay que hacer lo siguiente:
            if comment is None:
                comment = ALL_IDS_TO_COMMENTS.get(
                    pid)  # Cogemos el padre real
                # Pero lo "igoramos" para representarlo más tarde diciendo con ignored=True
                parent = Node(data=comment, sid=None, id=pid, parent=None, children=[
                              nuevoNodo, ], ignored=True, type="C", proposalid=comment.proposalid)

            else:
                parent = Node(data=comment, sid=None, id=pid, parent=None, children=[
                              nuevoNodo, ], type="C", proposalid=comment.proposalid)
                inserted.add(pid)
            nuevoNodo.parent = parent
            nuevoNodo = parent
            pid, parent = getParent(comentario=comment, tipo_son="C")

        parent.children.append(nuevoNodo)
        nuevoNodo.parent = parent
        return inserted

    def print_tree(self, prev_sid="", level: int = 0, index: int = 1, type=None, order_by: list = None, notoverridesid=False, nooutput=False, max_level=None, having: Callable = lambda t: True):
        partial = []
        if self.isroot():
            self.sid = self.TYPE
        elif self.TYPE == "P":
            self.sid = str(self.id)
            if nooutput is False:
                partial = [
                    "*" + self.TYPE + (self.sid or "?1?") + "*: " + repr(self.data) + '\n']

        elif type is not None and having(self) and (self.TYPE == type or type == "ALL"):

            if not notoverridesid:
                self.sid = str(self.id)

            partial = [(("_" + prev_sid + "_") if prev_sid != "" else "") + "->|"*(level-1) + "*" + (self.TYPE +
                       (self.sid or "?2?")) + '*: ' + repr(self.data if not self.ignored else "(No adecuado a búsqueda)")]
        j = 1
        children = self.children
        if order_by is not None and len(order_by) > 0:
            children = sorted(self.children, key=sorter(
                order_by), reverse="ordeninverso" not in order_by)
        else:
            children = self.children if type == "A" else sorted(
                self.children, key=lambda c: c.data.date if c.TYPE == "C" else datetime.date.today(), reverse=True)
            """sorted(self.children, key=lambda n: int(n.sid.split(".")[-1]) if (n.sid is not None and n.TYPE != "A") else (
                int(n.data.sentid) * 1000000 + int(n.data.aid)) if (n.sid is not None and n.TYPE == "A") else n.id, reverse=False)"""
        if max_level is None or level < max_level:
            for c in children:
                pt = c.print_tree(prev_sid if self.TYPE != "P" else (self.TYPE + str(self.id)), level+1, j, type=type,
                                  order_by=order_by, notoverridesid=notoverridesid, max_level=max_level, having=having)

                if nooutput is False:
                    partial.extend(pt)
                j += 1
        return partial

    def print_tree_advanced(self, prev_sid="", level: int = 0, index: int = 1, type=None, order_by: list = None, notoverridesid=False, nooutput=False, max_level=None, having: Callable = lambda t: True):
        # (Versión antigua con SIDs)
        partial = []
        if self.isroot():
            self.sid = self.TYPE
        elif self.TYPE == "P":
            self.sid = str(index)
            if nooutput is False:
                partial = [
                    "*" + self.TYPE + (self.sid or "?1?") + "*: " + repr(self.data if not self.ignored else "(No adecuado a búsqueda)") + '\n']

        elif type is not None and having(self) and (self.TYPE == type or type == "ALL"):

            if not notoverridesid:
                if level == 1:
                    self.sid = str(index)
                else:

                    self.sid = prev_sid + "." + (str(index) if self.TYPE != "A" else (str(str(
                        self.data.sentid)+":"+str(self.data.aid)) if not self.ignored else "(No adecuado a búsqueda)"))

            partial = ["--"*level + " " + ("*" if level in [1, 2] else "") + self.TYPE +
                       (self.sid or "?2?") + ("*" if level in [1, 2] else "") + ' ' + repr(self.data if not self.ignored else "(No adecuado a búsqueda)")]
        j = 1
        children = self.children
        if order_by is not None and len(order_by) > 0:
            children = sorted(self.children, key=sorter(
                order_by), reverse="ordeninverso" not in order_by)
        else:
            children = self.children if type == "A" else sorted(
                self.children, key=lambda c: c.data.date if c.TYPE == "C" else datetime.date.today(), reverse=True)
            """sorted(self.children, key=lambda n: int(n.sid.split(".")[-1]) if (n.sid is not None and n.TYPE != "A") else (
                int(n.data.sentid) * 1000000 + int(n.data.aid)) if (n.sid is not None and n.TYPE == "A") else n.id, reverse=False)"""
        if max_level is None or level < max_level:
            for c in children:
                pt = c.print_tree_advanced((self.sid or "?3?"), level+1, j, type=type,
                                           order_by=order_by, notoverridesid=notoverridesid, max_level=max_level, having=having)
                if nooutput is False:
                    partial.extend(pt)
                j += 1
        return partial

    def getNodeHaving(self, filter_fun: Callable, proposalid: int, type: str):

        if self.TYPE == "ROOT" and proposalid > -1 and proposalid in self.proposals.keys():
            return self.proposals[proposalid].getNodeHaving(filter_fun, proposalid, type)

        if (self.TYPE == type or type == "ALL") and filter_fun(self):
            return self
        else:
            for c in self.children:
                nod = c.getNodeHaving(filter_fun, proposalid, type)
                if nod is not None:
                    return nod
        return None

    def getAllNodesHaving(self, filter_fun: Callable, proposalid: int, type: str):

        if type == "P" and self.TYPE == "ROOT":
            return filter(filter_fun, self.proposals.values())
        elif self.TYPE == "ROOT" and proposalid != DONT_BOTHER_ABOUT_PROPOSAL:
            return self.proposals[proposalid].getAllNodesHaving(filter_fun, proposalid, type)

        matching_nodes = []
        if self.data is not None and (self.TYPE == type or type == "ALL") and filter_fun(self):
            matching_nodes.append(self)
        for c in self.children:
            matchings = c.getAllNodesHaving(filter_fun, proposalid, type)
            matching_nodes.extend(matchings)
        return matching_nodes

    def fold_tree(self, base: Any, folder: Callable, aggregation: Callable, type: str, filter_fun: Callable = lambda n: True, proposalid: int = -1):
        if self.isroot() or (self.TYPE != type and type != "ALL"):
            val = base
        elif filter_fun(self) is False:
            val = base
        else:
            val = aggregation(self)
        if type == "P" and proposalid == DONT_BOTHER_ABOUT_PROPOSAL:
            filtered = filter(filter_fun, self.proposals.values())
        elif self.TYPE == "ROOT" and self.proposalid is not None and proposalid != DONT_BOTHER_ABOUT_PROPOSAL and len(self.proposals) > 0:
            return self.proposals[proposalid].fold_tree(base, folder, aggregation, type, filter_fun, proposalid)
        elif type == "P" and proposalid is not None and proposalid != DONT_BOTHER_ABOUT_PROPOSAL:
            filtered = filter(filter_fun, self.proposals[proposalid])
        elif self.TYPE == "ROOT" and type != "P":
            filtered = self.proposals.values()
        else:
            filtered = filter(lambda n: (n.TYPE !=
                              type) or filter_fun(n), self.children)

        for c in filtered:
            val_child = c.fold_tree(
                base, folder, aggregation, type, filter_fun, proposalid)
            val = folder(val_child, val)
        return val

    def count(self, proposalid: int = -1, type="C", filter_fun: Callable = lambda n: True):
        return self.fold_tree(base=0, folder=Node.suma, aggregation=Node.present, type=type, proposalid=proposalid, filter_fun=filter_fun)

    def onfavor(n):
        if n.TYPE == "A":
            return n.data.relationtype == "support"
        return False

    def onattack(n):
        if n.TYPE == "A":
            return n.data.relationtype == "attack"
        return False

    def onqualifier(n):
        if n.TYPE == "A":
            return n.data.relationtype == "qualifier" or n.data.relationtype not in {"support", "attack"}
        return False

    def allArgumentedStreams(self):

        if self.TYPE == "A":
            return {self.parent}
        else:
            all_candidates = set()
            for c in self.children:
                maybe = c.allArgumentedStreams()
                if maybe is None or len(maybe) == 0:
                    continue
                if self.id in [x.id for x in maybe]:
                    return {self}
                all_candidates = all_candidates.union(maybe)

            return all_candidates

    def get_statistics(self, type: str, query: str, proposalid: int = -1, group_by=lambda t: True):
        returned = {}
        if type == "A":

            if query == "ALL":
                afavor = self.count(
                    type="A", filter_fun=lambda t: Node.onfavor(t) and group_by(t), proposalid=proposalid)
                nfavor = self.count(
                    type="A", filter_fun=lambda t: Node.onattack(t) and group_by(t),  proposalid=proposalid)
                qfavor = self.count(
                    type="A", filter_fun=lambda t: Node.onqualifier(t) and group_by(t),  proposalid=proposalid)
                if afavor + nfavor+qfavor == 0:
                    return None

                allargs = self.getAllNodesHaving(
                    filter_fun=lambda t: t.TYPE == "A" and group_by(t), type="A", proposalid=proposalid)
                totalargs = len(allargs)
                if totalargs == 0:
                    return None
                entities_perarg = [v for k, v in ARGS_TO_ENTITIES.items() if k in [
                    int(a.id) for a in allargs]]
                entities_claim = dict()
                for lista in entities_perarg:
                    for tupla in lista:
                        entities_claim[str(tupla[0])] = entities_claim.get(str(
                            tupla[0])) + int(tupla[1]) if entities_claim.get(str(tupla[0])) is not None else tupla[1]
                entities_claim = [{k: entities_claim.get(k)} for k in sorted(
                    entities_claim, key=entities_claim.get, reverse=True)][0:MAX_ENTITIES_IN_STATS]
                """{"Entidades más comunes":
                        entities_claim
                     },"""

                aspectos = [a.data.aspect for a in allargs]
                aspectos_dic = {a: None for a in aspectos}
                aspectos_dic = [{"\["+str(ord + 1)+"] " + str(k): aspectos.count(k)} for ord, k in enumerate(
                    sorted(aspectos_dic, key=aspectos.count, reverse=True))][0:MAX_ASPECTS_IN_STATS]

                cats = [(a.data.category, a.data.subcategory) for a in allargs]
                cats_dic = {a: None for a in cats}
                cats_dic = [{"\["+str(ord + 1)+"] " + Arguments.traducir(k[0])+"("+Arguments.traducir_to_emoji(k[0])+"), " + Arguments.traducir(k[1])+"("+Arguments.traducir_to_emoji(k[1])+")":str(
                    cats.count(k)) + " | " + "{:.2f}%".format(cats.count(k)/len(cats)*100)} for ord, k in enumerate(sorted(cats_dic, key=cats.count, reverse=True))][0:MAX_ASPECTS_IN_STATS]

                returned = [
                    {"Argumentos *a favor*   (🟩)": str(afavor) +
                     " | " + "{:.2f}%".format(afavor/totalargs*100)},
                    {"Argumentos *en contra* (🟥)": str(nfavor) +
                     " | " + "{:.2f}%".format(nfavor/totalargs*100)},
                    {"Argumentos *neutrales* (🟨)": str(qfavor) +
                     " | " + "{:.2f}%".format(qfavor/totalargs*100)},

                    {"*Intenciones* más comunes en los argumentos":
                        cats_dic
                     },
                    {"Discusiones argumentadas *más relevantes*": self.get_more_whatever(
                        tipo="ALL", limit=MAX_ARGS_STATS_PER_QUERY, measure_on_node=lambda t: 1 if t.TYPE == "A" else 0, on_list=self.allArgumentedStreams())},

                ]
            else:
                commentid = int(query)
                cnode = self.getNodeById(
                    id=commentid, proposalid=proposalid, type="C")  # Node de comentarios
                return cnode.get_statistics(type, "ALL", proposalid=proposalid, group_by=group_by)

        elif type == "C":
            if query != "ALL":
                # A partir de comentario con id = query
                comm: Node = self.getCommentNode(query, self.proposalid)
                returned = [
                    {"Número de respuestas": len(
                        list(filter(group_by, comm.children)))},
                    {"Votos": {"Positivos": comm.data.numpositivevotes,
                               "Negativos": comm.data.numnegativevotes}},
                    {"Número de respuestas a todos los niveles": comm.count(
                        type="C", proposalid=self.proposalid)},
                    {"{}".format("Se refiere a la propuesta" if comm.data.parentid == -
                                 1 else "Comentario padre"): repr(comm.parent.data)},
                    {"Discusiones más populares":
                        self.get_more_whatever(tipo="C", limit=MAX_POPULAR_COMMENTS, measure_on_node=lambda t: t.data.numvotes and group_by(
                            t), on_list=comm.children)
                     }

                ]
            else:
                if len(self.children) == 0:
                    returned = None
                else:
                    p_or_c = len(self.proposals) > 1
                    target_p_or_c_nodes = list(filter(group_by, self.proposals.values(
                    )) if p_or_c else filter(group_by, self.children[0].children))
                    longitud_hilos = [
                        (p.id, p.count(p.id, type="C")) for p in target_p_or_c_nodes
                    ] if p_or_c else [
                        (c.id, c.count(c.proposalid, type="C")) for c in target_p_or_c_nodes
                    ]

                    returned = [
                        {"Discusiones iniciadas sobre la propuesta" if not p_or_c else "Número de propuestas en la búsqueda": len(
                            target_p_or_c_nodes)},
                        {"Media de comentarios": float("{:.2f}".format(
                            sum(map(lambda l: l[1], longitud_hilos))/len(longitud_hilos)))},
                        {"Discusiones más controvertidas" if not p_or_c else "Propuestas más controvertidas": self.get_more_whatever(tipo="P", limit=MAX_POPULAR_COMMENTS, measure_on_node=lambda p: PROPS_TO_CONTROVERSY[p.id], on_list=target_p_or_c_nodes, filter=lambda c: c.TYPE == "P")

                            if p_or_c
                            else self.get_more_whatever(tipo="C", limit=MAX_POPULAR_COMMENTS, measure_on_node=lambda c: controversia_comentario(c.data), on_list=target_p_or_c_nodes)
                         },
                        {"Comentario más apoyado": (
                            self.get_more_whatever(tipo="C", limit=1, measure_on_node=lambda s: s.data.numpositivevotes, on_list=self.getAllNodesHaving(
                                lambda t: t.ignored == False, type="C", proposalid=DONT_BOTHER_ABOUT_PROPOSAL))
                        )},
                        {"Comentario más criticado": (
                            self.get_more_whatever(tipo="C", limit=1, measure_on_node=lambda s: s.data.numnegativevotes, on_list=self.getAllNodesHaving(
                                lambda t: t.ignored == False, type="C", proposalid=DONT_BOTHER_ABOUT_PROPOSAL))
                        )}

                    ]
        return returned

    def copy(self):
        return Node(self.data, self.sid, self.id, self.parent, self.children.copy(), self.TYPE, proposalid=self.proposalid)

    def getProposalNode(self, idprop: int):
        return self.getNodeById(id=idprop, proposalid=idprop, type="P")

    def getCommentNode(self, idcom: int, propid: int):
        return self.getNodeById(id=idcom, proposalid=propid, type="C")

    def addArgumentToTree(self, arg: Arguments):
        node = Node(arg, sid=None, id=arg.id, children=[],
                    parent=None, type="A", proposalid=arg.proposalid)
        if arg.commentid == -1:
            parent: Node = self.getProposalNode(idprop=arg.proposalid)
        else:
            parent: Node = self.getCommentNode(arg.commentid, arg.proposalid)
        if parent is not None:
            if parent.sid is not None:
                node.sid = parent.sid.replace(
                    parent.TYPE, self.TYPE) + "." + str(arg.sentid)
            node.parent = parent
            parent.children.append(node)
        return self

    def suma(x, y):
        return x + y

    def present(x):
        return 1

    def setOfTwo(x: Set, y: Set):
        return x.union(y)
