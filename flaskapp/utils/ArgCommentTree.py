
from sys import stderr
import time
from typing import Any, Callable, Dict, List, Set
from flask_sqlalchemy.model import Model
from sqlalchemy.sql.elements import BinaryExpression
from sqlalchemy.sql.expression import asc, desc,  and_
from flaskapp.models import ArgCategories,  ArgLinker, ArgSubcategories, Arguments, MetricsControversy, ProposalComments, ProposalTopics, Proposals
import yaml
from flaskapp.proposals import DEFAULT_CONTROVERSY

from flaskapp.utils.Node import DONT_BOTHER_ABOUT_PROPOSAL, Node
from flaskapp.utils.NodeData import NodeData
from flaskapp.utils.df_response import DFresponse
TYPES = ['proposals', 'topics', '']

GROUPBY = {
    "temas": "topic",
    "aspectos": "aspect",
    "argcategory": "category",
    "argsubcategory": "subcategory"
}


def get_groups(arg: Arguments, group_by):
    return tuple(
        arg.__getattribute__(GROUPBY.get(g)) for g in group_by)


def generateCommentTrees(allcomments: Set[NodeData], proposals: List[Proposals] = None):
    return generateObjectTrees(allcomments, proposals, type="C")


def generateObjectTrees(data: Set[Any], proposals: List[Proposals], type: str):
    allcomments_to_thier_ids = dict()
    for c in data:
        allcomments_to_thier_ids[c.id] = c

    if proposals is not None:
        commenttree = Node(data=None, type="ROOT", sid=None, id=None, children=[Node(data=p, sid=str(
            idx+1), id=p.id, parent=None, children=[], type="P") for idx, p in enumerate(proposals)])

    already_inserted = set()
    ins = 0
    for id, c in allcomments_to_thier_ids.items():
        ins += 1
        if id not in already_inserted:
            inserted = commenttree.link_data(
                comment=c, allcomments=allcomments_to_thier_ids, type=type)

        already_inserted.update(inserted)
    return allcomments_to_thier_ids, commenttree


def generateArgId(arg: Arguments):
    if arg.commentid == -1:
        return "P" + str(arg.proposalid) + "-" + str(arg.sentid)
    else:
        return "S" + str(arg.proposalid) + "-" + str(arg.sentid)


def generateArgumentTrees(commentTree: Node, allargs:  List[Arguments]):

    all_arguments_to_their_ids: Dict[int, Arguments] = dict()
    for a in allargs:
        all_arguments_to_their_ids[a.id] = a
        commentTree.addArgumentToTree(a)
    return all_arguments_to_their_ids, commentTree


def traducir_grupo(g):
    return Arguments.traducir(g.upper()) + ("({})".format(Arguments.traducir_to_emoji(g.upper())) if Arguments.traducir_to_emoji(g.upper()) != Arguments.traducir(g.upper()) else "")


class ArgCommentTree:
    def copy(self):
        return self.restricted_by(par=self.par, joins=self.joins, propid=self.proposalid, from_proposals=self.from_proposals, pseudo_filtros=self.pseudo_filtros)

    def isempty(self):
        return len(self.argTree) == 0

    def restricted_by(self, par=True, joins=set(), propid=DONT_BOTHER_ABOUT_PROPOSAL, pseudo_filtros=None, from_proposals=None):
        if par is None or par is True:
            newpar = self.par
        else:
            newpar = and_(self.par, par)
        newjoins = self.joins.union(joins or set())
        newpropid = propid if self.proposalid == DONT_BOTHER_ABOUT_PROPOSAL else self.proposalid

        return ArgCommentTree(newpar, newjoins, newpropid, from_proposals=from_proposals if newpropid < 0 else newpropid, pseudo_filtros=pseudo_filtros)

    def __init__(self, par=None, joins: Set[Model] = set(), propid: int = DONT_BOTHER_ABOUT_PROPOSAL, from_proposals=None, pseudo_filtros=None):
        self.par: BinaryExpression = par
        self.joins: set = joins
        self.commentTree = dict()
        self.argTree = dict()

        self.argSearchTree: Node = None
        self.proposalid = propid
        self.from_proposals = from_proposals

        if propid != DONT_BOTHER_ABOUT_PROPOSAL:
            self.joins.add(Proposals)
            if self.par is None:
                self.par = Proposals.id == self.proposalid

            self.par = and_(self.par, Proposals.id == self.proposalid)

        elif self.from_proposals is not None:
            if self.par is None:
                self.par = Proposals.id.in_(
                    list(map(lambda data: data.id, self.from_proposals)))
            else:
                self.par = and_(self.par, Proposals.id.in_(
                    list(map(lambda data: data.id, self.from_proposals))))
            self.joins.add(Proposals)
        self.joins.add(MetricsControversy)

        self.proposals_query = Proposals.query.with_entities(
            Proposals).filter(self.par)
        self.allcomments_query = ProposalComments.query.with_entities(
            ProposalComments).filter(self.par)
        # Argumentos:
        self.allargs_query = Arguments.query.with_entities(
            Arguments).filter(Arguments.treelevel < 3).filter(self.par)

        if ArgCategories in self.joins or ArgSubcategories in self.joins or ArgLinker in self.joins:
            try:
                self.joins.remove(Arguments)
            except KeyError:
                pass
            try:
                self.joins.remove(ArgLinker)
            except KeyError:
                pass

            self.proposals_query = self.proposals_query.join(
                Arguments, Arguments.proposalid == Proposals.id
            ).join(
                ArgLinker, ArgLinker.id == Arguments.linker
            )
            self.allcomments_query = self.allcomments_query.join(
                Arguments, and_(Arguments.commentid == ProposalComments.id,
                                Arguments.proposalid == ProposalComments.proposalid)
            ).join(
                ArgLinker, ArgLinker.id == Arguments.linker
            )
            self.allargs_query = self.allargs_query.join(
                ArgLinker, ArgLinker.id == Arguments.linker
            )

        for j in self.joins:

            if j == Proposals:
                self.allcomments_query = self.allcomments_query.join(
                    Proposals, Proposals.id == ProposalComments.proposalid
                )
                self.allargs_query = self.allargs_query.join(
                    Proposals, Proposals.id == Arguments.proposalid
                )
            elif j == ProposalTopics:
                self.proposals_query = self.proposals_query.join(
                    ProposalTopics, ProposalTopics.id == Proposals.id
                )
                self.allcomments_query = self.allcomments_query.join(
                    ProposalTopics, ProposalTopics.id == ProposalComments.proposalid
                )
                self.allargs_query = self.allargs_query.join(
                    ProposalTopics, ProposalTopics.id == Arguments.proposalid
                )
            elif j == ProposalComments:
                self.proposals_query = self.proposals_query.join(
                    ProposalComments, ProposalComments.proposalid == Proposals.id
                )
                self.allargs_query = self.allargs_query.join(
                    ProposalComments, ProposalComments.proposalid == Arguments.proposalid
                )
            elif j == Arguments:
                self.proposals_query = self.proposals_query.join(
                    Arguments, Arguments.proposalid == Proposals.id
                )
                self.allcomments_query = self.allcomments_query.join(
                    Arguments, and_(Arguments.commentid == ProposalComments.id,
                                    Arguments.proposalid == ProposalComments.proposalid)
                )
            elif j == ArgCategories:
                self.allargs_query = self.allargs_query.join(
                    ArgCategories, ArgCategories.name == ArgLinker.category
                )
                self.proposals_query = self.proposals_query.join(
                    ArgCategories, ArgCategories.name == ArgLinker.category
                )
                self.allcomments_query = self.allcomments_query.join(
                    ArgCategories, ArgCategories.name == ArgLinker.category
                )
            elif j == ArgSubcategories:
                self.allargs_query = self.allargs_query.join(
                    ArgSubcategories, ArgSubcategories.name == ArgLinker.subcategory
                )
                self.proposals_query = self.proposals_query.join(
                    ArgSubcategories, ArgSubcategories.name == ArgLinker.subcategory
                )
                self.allcomments_query = self.allcomments_query.join(
                    ArgSubcategories, ArgSubcategories.name == ArgLinker.subcategory
                )
            elif j == MetricsControversy:
                self.proposals_query = self.proposals_query.join(
                    MetricsControversy, MetricsControversy.proposalid == Proposals.id)
                self.allcomments_query = self.allcomments_query.join(
                    MetricsControversy, ProposalComments.proposalid == MetricsControversy.proposalid)
                self.allargs_query = self.allargs_query.join(
                    MetricsControversy, MetricsControversy.proposalid == Arguments.proposalid
                )
        """
        self.proposals_query = self.proposals_query.filter(par)
        self.allargs_query = self.allargs_query.filter(par)
        self.allcomments_query = self.allcomments_query.filter(par)"""
        """self.first_level_args_query = self.allcomments_query.filter(
            Arguments.parentid == -1)
        self.first_level_comments_query = self.allcomments_query.filter(
            ProposalComments.parentid == -1)"""
        self.comments_all: List[NodeData] = [
            NodeData(c, tipo="C") for c in self.allcomments_query.all()]
        self.proposals_all: List[NodeData] = [
            NodeData(p, tipo="P") for p in self.proposals_query.all()]
        self.arguments_all: List[NodeData] = [
            NodeData(a, tipo="A") for a in self.allargs_query.all()]
        self.pseudo_filtros = pseudo_filtros
        if self.pseudo_filtros is not None and len(self.pseudo_filtros) > 0:
            self.arguments_all = set(a for a in self.arguments_all if all(
                [ps(a) for ps in pseudo_filtros]))
            self.comments_all = set(c for c in self.comments_all if (
                c.id in [a.commentid for a in self.arguments_all]))
            self.proposals_all = set(p for p in self.proposals_all if (
                p.id in [a.proposalid for a in self.arguments_all]))
        self.remake()

    def remake(self, ordered=False, notoverride=True):

        start = time.time()
        print("START")
        if ordered:
            ordered_props = [NodeData(op, tipo="P")
                             for op in self.proposals_query_ordered.all()]
            if self.pseudo_filtros is not None and len(self.pseudo_filtros) > 0:
                ordered_props = [p for p in ordered_props if (
                    p.id in [a.proposalid for a in self.arguments_all])]
        _, ct = generateCommentTrees(
            self.comments_all, self.proposals_all if ordered == False else ordered_props)

        self.argTree, self.argSearchTree = generateArgumentTrees(ct,
                                                                 self.arguments_all)

        print((time.time() - start), file=stderr)
        print("DONE REMAKE")
        self.argSearchTree.print_tree(
            type="ALL", nooutput=True)  # Asigna SID a los nodos
        print((time.time() - start), file=stderr)
        print("DONE SIDS")

    def order_by(self, orders):
        self.proposals_query_ordered = self.proposals_query
        if orders is None or len(orders) == 0:
            return
        did_order = False
        for o in orders:
            if o == "ordeninverso":
                did_order = True
                continue
            if o == "ordencontroversia":
                did_order = True
                self.proposals_query_ordered = self.proposals_query_ordered.filter(MetricsControversy.name == DEFAULT_CONTROVERSY).order_by(
                    asc(MetricsControversy.value) if "ordeninverso" in orders else desc(
                        MetricsControversy.value)
                )

            elif o == "ordenvotos":
                did_order = True
                self.proposals_query_ordered = self.proposals_query_ordered.order_by(
                    asc(Proposals.numsupports) if "ordeninverso" in orders else desc(
                        Proposals.numsupports)
                )
                """
        print("QUERY ORDERED")
        print(self.proposals_query_ordered)"""
        if did_order:
            print("REMAKING with orders: " + str(orders))
            self.remake(ordered=True)

    def try_get_things(self, type, order_by, having: Callable = lambda t: True):
        error = [], "Comentarios" if type == "C" else "Argumentos"
        try:
            res = self.argSearchTree.print_tree(
                type=type, order_by=order_by, notoverridesid=False, having=having)
        except IndexError:
            return error
        except KeyError:
            return error
        return res, "Comentarios" if type == "C" else "Argumentos"

    def print_tree_by_proposals(self, type="C", order_by: list = None, group_by: list = []):

        if len(group_by) == 0:
            self.order_by(order_by)
            return self.try_get_things(type, order_by)

        else:
            if "argcategory" in group_by:
                group_by.append("argsubcategory")

            groups = {get_groups(arg.data, group_by) for arg in self.argSearchTree.getAllNodesHaving(
                lambda t: True, type=type, proposalid=self.proposalid)}
            print("GROUPING BY: ")
            print(groups)
            reses = list()
            for gb in groups:
                def having(node: Node):
                    if node.TYPE != type:
                        if node.getNodeHaving(lambda t: t.TYPE == type, self.proposalid, type="ALL"):
                            return True
                        return False
                    return get_groups(node.data, group_by) == gb

                reses.append(yaml.dump(["Agrupando por "] + list(
                    map(lambda g: "*" + traducir_grupo(g) + "*", gb)), allow_unicode=True, width=28))
                reses.append("----------------------------")
                reses.extend(self.try_get_things(
                    type, order_by, having=having)[0])
                reses.append("----------------------------")
            return reses, "Comentarios" if type == "C" else "Argumentos"

    def comment_statistics(self, commid, pid, aclaracion="", withargs=True):
        stats = self.argSearchTree.get_statistics(
            "C", query=commid, proposalid=pid)
        c = self.argSearchTree.getCommentNode(commid, propid=pid)
        bots = [[{
            "text": "Ver propuesta",
            "callback_data": "Propuesta con id {}".format(pid)
        }] if c.data.parentid == -1 else [{
            "text": "Ver propuesta",
            "callback_data": "Propuesta con id {}".format(pid)
        }, {
            "text": "Ver padre",
            "callback_data": "Ver comentario con id {}".format(c.data.parentid)
        }],
            [{
                "text": "Ver estadísticas argumentales"
            }] if withargs else []
        ]
        returned_str: str = "\nEstadísticas de las respuestas del comentario\n{}\n".format(
            c.data)
        if stats is None:
            return DFresponse("\[ERROR] No se han obtenido resultados. Puede que no haya argumentos reconocibles bajo el comentario indicado (cid: {})".format(commid))
        return DFresponse(aclaracion + returned_str + yaml.dump(allow_unicode=True, data=stats, indent=4, width=28) + "\nEscribe Ver comentarios para verlos", botones=bots)

    def general_statistics(self, withargs, type="A", aclaracion="", group_by=[], having=lambda t: True):

        if len(group_by) == 0:
            pass

        else:
            if "argcategory" in group_by:
                group_by.append("argsubcategory")

            groups = {get_groups(arg.data, group_by) for arg in self.argSearchTree.getAllNodesHaving(
                lambda t: True, type=type, proposalid=self.proposalid)}
            print("GROUPING BY:")
            print(groups)
            reses = list()
            for gb in groups:
                def having(node: Node):
                    if node.TYPE != type:
                        if node.getNodeHaving(lambda t: t.TYPE == type, self.proposalid, type="ALL"):
                            return True
                        return False
                    return get_groups(node.data, group_by) == gb

                reses.append("Agrupando por...\n" + yaml.dump(
                    list(map(lambda g: "*" + traducir_grupo(g) + "*", gb)), allow_unicode=True))
                reses.append("Estadísticas:"+"\n"+yaml.dump(self.argSearchTree.get_statistics(
                    type, "ALL", proposalid=self.proposalid, group_by=having), allow_unicode=True, width=28))
                reses.append("----------------------------")
            return reses, "Comentarios" if type == "C" else "Argumentos"

        print("START STATS")
        start = time.time()
        stats = self.argSearchTree.get_statistics(type, "ALL",
                                                  proposalid=self.proposalid)
        print((time.time() - start), file=stderr)
        print("DONE STATS")

        if stats is None or stats == "No hay propuestas sobre las que partir, o éstas no tenían comentarios":
            return DFresponse(aclaracion + "\[ERROR] No se han obtenido resultados. Puede que no haya {} sobre este subconjunto de propuestas. Tenga en cuenta que cuando el chatbot filtra los árboles, se hace de forma acumulada a los resultados anteriores. Es decir, si usted indica _'Ver comentarios que contengan \"cierto texto\"'_ pero luego escribe _'Ver comentarios que contengan \"cierto otro texto\"'_, se entenderá que busca comentarios que contengan *AMBOS* textos, y así con todos las demás formas de _filtrar_.\n\nSi quieres salir de este filtrado acumulado, escribe _Volver_ para volver al punto de partida sin filtros".format("comentarios" if type == "C" else "argumentos"))

        returned_str: str = "\nBajo los criterios de búsqueda especificados, se han obtenido:\n"
        if self.proposalid != DONT_BOTHER_ABOUT_PROPOSAL:
            returned_str = returned_str + "Estadísticas de {} sobre la propuesta:\n{}\n_{}_\n\n".format(
                "*argumentos*" if type == "A" else "*comentarios*", repr(self.proposals_all[0]), self.proposals_all[0].summary.replace('_', '').replace('*', ''))
        bots = [[{
            "text": "Árbol comentarios",
            "callback_data": "Ver comentarios"
        },
            {
            "text": "Árbol argumentos",
            "callback_data": "Ver argumentos"
        }] if withargs else [{
            "text": "Árbol comentarios",
            "callback_data": "Ver comentarios"
        }], [{
            "text": "Árbol completo",
            "callback_data": "Ver argumentos y comentarios"
        }] if withargs else [],
            [{
                "text": "A favor",
                "callback_data": "Argumentos a favor"
            }, {
                "text": "Neutrales",
                "callback_data": "Argumentos matizantes"
            },
            {
                "text": "En contra",
                "callback_data": "Argumentos en contra"
            }] if withargs and (type == "A" or type == "ALL") else []]
        dum = bots.append([{
            "text": "Ver detalle de propuesta",
            "callback_data": "Ver propuesta con pid {}".format(self.proposalid)
        }]) if self.proposalid != DONT_BOTHER_ABOUT_PROPOSAL else None
        return DFresponse(aclaracion + returned_str + yaml.dump(allow_unicode=True, data=stats, indent=2, width=28), botones=bots)
