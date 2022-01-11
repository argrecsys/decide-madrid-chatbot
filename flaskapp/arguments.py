from flaskapp.models import ProposalComments, ProposalTopics, Proposals, Users
from sqlalchemy.sql.expression import or_
from typing import Callable, Tuple
import traceback
from sys import stderr
from typing import Any, List
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import and_, or_

from flaskapp.models import (
    ArgCategories,
    ArgClaim,
    ArgLinker,
    ArgSubcategories,
    Arguments,
    ProposalComments,
    Proposals,
    ProposalTopics,
    Users,
)
from flaskapp.utils.ArgCommentTree import ArgCommentTree
from flaskapp.utils.NodeData import NodeData
from flaskapp.utils.df_request import DFrequest
from flaskapp.utils.df_response import DFresponse
from flaskapp.utils.df_utils import ARGS_TO_ENTITIES
import yaml
MAX_ARGS_PER_QUERY = 4


def detalle_argumento(a: NodeData,  p: Proposals, c: ProposalComments = None, sid: str = None, withargs=True):
    premise: ArgClaim = a.premisetext
    claim: ArgClaim = a.claimtext
    res = "El argumento indicado tiene estas características:\n"
    text = a.escribir_sentence() if a.sentence is not None else "(SENTENCE NOT AVAILABLE)"
    url = p.url
    user = Users.query.get(
        c.userid) if c is not None else Users.query.get(p.userid)
    username = user.name
    a: NodeData = NodeData(a, tipo="A")

    res = "*A{}* - Argumento {}({}) de la propuesta P{}{}{} por {}\nURL propuesta: {}\n\n{}\n{}\n{}".format(
        a.id,
        "positivo-apoyo" if a.relationtype == "support" else "negativo-atacante" if a.relationtype == "attack" else "neutral-matizante",
        Arguments.traducir_to_emoji(a.relationtype),
        p.id,
        " realizado en el comentario '_base_' C{}".format(sid.replace(
            "A", "C") if sid is not None else c.id) if c is not None else "",
        ", el cual responde al comentario '_raíz_' C{}".format(
            a.parentid) if a.parentid != -1 else "",
        username,
        "https://decide.madrid.es/"+url,
        text,
        "El argumento, con carácter {}, tiene la intencionalidad {}({})-{}({}) contra la _afirmación_ (en cursiva)\n\n\"_{}_\"\n\nexpresando la *premisa* (negrita):\n\n\"*{}*\"\n\nEl conector \"*{}*\", une ambas expresiones.\n\n".format(
            "positivo-apoyo" if a.relationtype == "support" else "negativo-atacante" if a.relationtype == "attack" else "neutral-matizante",
            Arguments.traducir(a.category),
            Arguments.traducir_to_emoji(a.category),
            Arguments.traducir(a.subcategory),
            Arguments.traducir_to_emoji(a.subcategory),
            claim.replace('_', ''), premise.replace('_', ''),
            a.linkertext
        ),
        #"{}".format("Y se habla de estas _entidades_ (objetos a los que se refiere el autor en su argumento):\n   {}".format(yaml.dump({e[0]:e[1] for e in a.entities}, allow_unicode=True, indent=4) if  len(a.entities or ()) > 0 else "") if  len(a.entities or ()) > 0 else "No se detectaron _entidades_ (objetos a los que se refiere el autor en su argumento)" ) ,
        "El _comentario base_ (del que se extrajo el argumento) tiene *{} votos*{}".format(c.numvotes, ", de los cuales:\n   -{} {}👍\n   -{} {}👎\n".format(c.numpositivevotes, ("es voto positivo" if c.numpositivevotes == 1 else "son votos positivos",
                                                                                                                                                                                c.numnegativevotes, "es voto negativo" if c.numnegativevotes == 1 else "son votos negativos") if c is not None else "La propuesta tenía {} apoyos y {} comentarios".format(p.numsupports, p.numcomments)) if c.numvotes > 0 else "")
    )
    return DFresponse(res, botones=[
        [
            {
                "text": "Ver propuesta",
                "callback_data": "Detalle de la propuesta con pid {}".format(p.id)
            }
        ],
        [
            {
                "text": "Ver comentario raíz (C{})".format(a.parentid),
                "callback_data": "Ver comentario con id {}".format(a.parentid)
            },
        ] if a.parentid != -1 else [],
        [
            {
                "text": "Ver comentario base",
                "callback_data": "Ver comentario con id {}".format(a.commentid)
            }
        ] if a.commentid != -1 else [],

        [
            {
                "text": "Ver respuestas (argumentales)",
                "callback_data": "Ver argumentos del comentario con id {}".format(a.commentid)
            } if a.commentid != -1 else {
                "text": "Ver respuestas",
                "callback_data": "Ver argumentos de la propuesta con id {}".format(a.proposalid)
            },
            {
                "text": "Ver respuestas (comentarios)",
                "callback_data": "Ver comentarios del comentario con id {}".format(a.commentid)
            } if a.commentid != -1 else {
                "text": "Ver comentarios de la prop.",
                "callback_data": "Ver comentarios de la propuesta con id {}".format(a.proposalid)
            }
        ],
        [
            {
                "text": "RESPONDER AL COMENTARIO",
                "callback_data": "registrar comentario para el comentario con id {}".format(a.commentid)
            } if a.commentid != -1 else {
                "text": "RESPONDER A LA PROPUESTA",
                "callback_data": "registrar comentario para la propuesta con id {}".format(a.proposalid)
            }
        ],
        [
            {
                "text": "HACER UNA NUEVA PROPUESTA",
                "callback_data": "registrar propuesta similar a {}".format(p.id)
            }
        ],
        [
            {
                "text": "VOTAR POS. EL COMENTARIO",
                "callback_data": "registrar punto positivo a comentario {}".format(c.id)
            },
            {
                "text": "VOTAR NEG. EL COMENTARIO",
                "callback_data": "registrar punto negativo a comentario {}".format(c.id)
            }
        ] if c is not None else [{
            "text": "DAR MI APOYO A LA PROPUESTA",
            "callback_data": "registrar apoyo a propuesta {}".format(p.id)
        }]
    ])


def get_all_arguments_from_propuesta(
    propuesta: Proposals or ProposalComments, relationtype: str
):
    first_level_all = (
        Arguments.query.with_entities(Arguments)
        .join(ArgLinker, ArgLinker.id == Arguments.linker)
        .filter(Arguments.proposalid == propuesta.id)
    )
    all = first_level_all
    if relationtype != "ALL" and relationtype != "REST":
        all = first_level_all.filter(ArgLinker.relationtype == relationtype)
    elif relationtype == "REST":
        all = first_level_all.filter(ArgLinker.relationtype != "support").filter(
            ArgLinker.relationtype != "attack"
        )
    return all


def arg_writer(arg: Arguments):
    return repr(arg)


class Argumentos:

    dfr: DFrequest = None

    def __init__(
        self,
        dfr,
    ):
        self.dfr = dfr
        self.argCommentTree = None
        self.last_argCommentTree = None

    def get_something_by_sid(self, sid: str):
        try:
            return (ProposalComments.query.get if sid[0] == "C" else Arguments.query.get if sid[0] == "A" else Proposals.query.get)(self.last_argCommentTree.argSearchTree.getNodeBySid(sid).id)
        except Exception as e:
            print("Error when getting something by sid {}".format(
                sid) + str(e), file=stderr)
            return None

    def detalleComentarios(self, dfr: DFrequest) -> Tuple[DFresponse, str] or Callable[[None, Tuple[DFresponse, str]]]:

        if 'visualizar' in dfr.parameters:
            if dfr.parameters.get('visualizar') == "ver":
                return lambda: self.comentarios(dfr, order_by=dfr.parameters.get('orden'), visualizar=True)

        return self.comentarios(dfr, order_by=dfr.parameters.get('orden'), visualizar=False)

    def detalleArgumentos(self, dfr: DFrequest) -> Tuple[DFresponse, str] or Callable[[None, Tuple[DFresponse, str]]]:

        if 'visualizar' in dfr.parameters:
            if dfr.parameters.get('visualizar') == "ver":
                return lambda: self.argumentos(dfr, order_by=dfr.parameters.get('orden'), visualizar=True)

        return self.argumentos(dfr, order_by=dfr.parameters.get('orden'), visualizar=False)

    def comentarios(self, dfr: DFrequest, order_by: list, visualizar=True):
        return self.list_objects(dfr, order_by, type="C", visualizar=visualizar)

    def list_objects(self, dfr: DFrequest, order_by: list, type: str = "C", visualizar=False, dontrestrict=False, aclaracion=""):
        filtros = []
        pseudo_filtros = []
        joins = set()
        filtro = None
        group_by = list()
        if dfr.parameters.get('TipoBusqueda') is not None:
            for f in dfr.parameters.get('TipoBusqueda'):
                if "argscon" in f:
                    f = f.split("argscon")[1]
                    # Filtros temas, contenido, entidades, aspectos, argcategory
                    valores: List[str] = dfr.parameters.get(f)
                    if f == "temas":
                        if valores is None:
                            valores: List[str] = dfr.parameters.get("data")
                        filtros.append(or_(ProposalTopics.topic.like(
                            '%{}%'.format(v.casefold())) for v in valores))
                        joins.add(ProposalTopics)
                    elif f == "contenido":
                        valor: str = dfr.parameters.get("data")[0]
                        filtros.append((ProposalComments.text if type == "C" else Arguments.sentence).like(
                            "%{}%".format(valor)))
                        joins.add(ProposalComments) if type == "C" else joins.update(
                            {Arguments, ProposalComments})
                    elif f == "aspectos" and (type == "A" or type == "ALL"):
                        if valores is None:
                            valores: List[str] = dfr.parameters.get("data")
                        filtros.append(or_(Arguments.aspect.like(
                            '%{}%'.format(v.casefold())) for v in valores))
                        joins.add(Arguments)
                    elif f == "entidades" and (type == "A" or type == "ALL"):
                        if valores is None:
                            valores: List[str] = dfr.parameters.get("data")
                        pseudo_filtros.append(lambda arg: any(
                            [all([t in [val[0] for val in ARGS_TO_ENTITIES[arg.id]] for t in v.split(",")]) for v in valores]))
                        joins.add(Arguments)

                    elif f == "argcategory" and (type == "A" or type == "ALL"):
                        if valores is None:
                            valores: List[str] = dfr.parameters.get("data")
                        filtros.append(or_(or_(ArgCategories.name.like('%{}%'.format(Arguments.traducir_inverso(v).lower(
                        ))), ArgSubcategories.name.like('%{}%'.format(Arguments.traducir_inverso(v).lower()))) for v in valores))
                        joins.update(
                            {ArgCategories, ArgSubcategories, Arguments})
                elif "argspor" in f:
                    f = f.split("argspor")[1]
                    # Agrupacion por temas, contenido, entidades, aspectos, argcategory
                    group_by.append(f)
                elif "argsencontra" == f:
                    # En contra estadisticas o visualizar
                    filtros.append(Arguments.relationtype == "attack")
                    joins.add(Arguments)

                elif "argsafavor" == f:
                    filtros.append(Arguments.relationtype == "support")
                    joins.add(Arguments)
                elif "argsneutral" == f:
                    filtros.append(or_(Arguments.relationtype == "qualifier", Arguments.relationtype == "support/attack"))
                    joins.add(Arguments)

        filtro = and_(f for f in filtros)
        if self.argCommentTree is not None:
            if not dontrestrict:
                restricted_tree = self.last_argCommentTree.restricted_by(
                    par=filtro,
                    joins=joins,
                    propid=self.last_argCommentTree.proposalid,
                    from_proposals=self.last_argCommentTree.from_proposals,
                    pseudo_filtros=pseudo_filtros)
            else:
                restricted_tree = self.last_argCommentTree.copy()
        else:
            self.argCommentTree = ArgCommentTree(
                par=filtro, joins=joins, pseudo_filtros=pseudo_filtros)
            restricted_tree: ArgCommentTree = self.argCommentTree.copy()
        if not restricted_tree.isempty():
            self.last_argCommentTree = restricted_tree
        else:
            self.last_argCommentTree = self.argCommentTree

        if visualizar:
            return restricted_tree.print_tree_by_proposals(type, order_by=order_by, group_by=group_by)
        else:
            return restricted_tree.general_statistics(dfr.withargs, type, group_by=group_by, aclaracion=aclaracion)

    def argumentos(self, dfr: DFrequest, order_by: list, visualizar=True):
        tipo = "A"
        if dfr.parameters.get('TipoBusquedaComentarios') == "comentarios":
            tipo = "ALL"

        return self.list_objects(dfr, order_by, type=tipo, visualizar=visualizar)

    def get_sid_of(self, c: ProposalComments or Arguments, type="C"):
        try:
            print("SID" + str(self.argCommentTree.argSearchTree.getNodeById(c.id).sid))
            return self.argCommentTree.argSearchTree.getNodeById(c.id).sid
        except:
            return None

    def performArgSearch(self, data: Any, tipo="A", withargs=True) -> DFresponse:
        # return DFresponse(fulfillment_message=str(list(ArgClaim.query.limit(25)))).get_final_response(self.dfr)
        verarbol = self.dfr.parameters.get('visualizar') == "ver"
        orden = self.dfr.parameters.get(
            "orden") if self.dfr.parameters.get("orden") is not None else []

        if (
            data is None
        ):

            return DFresponse("Indique si quiere ver argumentos añadiendo si quiere verlos sobre las últimas propuestas que ha buscado (`Argumentos de las propuestas anteriores`) o indicando el título/id de una (`Argumentos de la porpuesta 494`). También puede buscar argumentos sobre un *tema* concreto (`Argumentos sobre el tema \"urbanismo\"`)")
        else:
            parsed_ok = False
            acl = "Resultados sobre últimos datos analizados"

            if type(data) == Proposals:
                print("Sacando argumentos/comm de la propuesta: " + repr(data))
                parsed_ok = True
                try:
                    comm = data
                    self.last_query = get_all_arguments_from_propuesta(
                        comm, "ALL")
                    if self.argCommentTree is None:
                        self.argCommentTree = ArgCommentTree(propid=comm.id)
                    self.last_argCommentTree = self.argCommentTree
                    return self.list_objects(self.dfr, order_by=orden, visualizar=verarbol, type=tipo, dontrestrict=True)

                except NoResultFound as e:
                    print(str(traceback.format_exc()), file=stderr)
                    raise NoResultFound(
                        "Ha ocurrido un error en la búsqueda de argumentos para la propuesta: "
                        + str(data)
                        + ", "
                        + str(e)
                    )
                except Exception as e:
                    print(str(traceback.format_exc()), file=stderr)
                    raise e

            elif type(data) == ProposalComments:
                parsed_ok = True
                if self.last_argCommentTree is None:
                    self.argCommentTree = ArgCommentTree(
                        propid=data.proposalid)
                    self.last_argCommentTree = self.argCommentTree
                val = self.argCommentTree.comment_statistics(
                    data.id, data.proposalid, withargs=withargs)
                return val

            elif type(data) == list:
                parsed_ok = True

                if self.last_argCommentTree is None:
                    acl = ""
                    self.argCommentTree = ArgCommentTree(from_proposals=data)
                    self.last_argCommentTree = self.argCommentTree

            elif type(data) == ProposalTopics:
                parsed_ok = True
                if self.last_argCommentTree is None:
                    acl = ""
                    print("Sacando argumentos por tema: " + repr(data))
                    self.argCommentTree = ArgCommentTree(
                        ProposalTopics.topic == data.topic, {ProposalTopics, })
                    self.last_argCommentTree = self.argCommentTree

            if parsed_ok:
                self.last_argCommentTree = self.argCommentTree
                return self.list_objects(self.dfr, order_by=self.dfr.parameters.get('orden'), type=tipo, aclaracion=acl, dontrestrict=True, visualizar=verarbol)
                # return self.last_argCommentTree.general_statistics(type=tipo, aclaracion=acl, withargs=withargs)
            else:
                return DFresponse("No se comprendió su petición, por favor vuelva a escribirla de forma legible para el chatbot")
