import os
import pickle
import re
import traceback
from datetime import datetime
from sys import stderr
from typing import Any, Callable, List, Tuple

from pydialogflow_fulfillment.dialogflow_response import DialogflowResponse

from sqlalchemy import or_
from sqlalchemy.sql.expression import asc, desc

from flaskapp.arguments import Argumentos
from flaskapp.models import *
from flaskapp.utils import logs
from flaskapp.utils.Node import MAX_ARGS_STATS_PER_QUERY
from flaskapp.utils.df_request import DFrequest
from flaskapp.utils.df_response import DFresponse
from flaskapp.utils.df_utils import list_to_telegram, quitar_tildes
from flaskapp.utils.logs import get_logs
import flaskapp.proposals as proposals
import flaskapp.comments as comments
import flaskapp.arguments as arguments
from flaskapp.utils import df_request

MAX_CATEGORIAS_PER_QUERY = 20
MAX_PROPUESTAS_PER_QUERY = 10
BASE_PICKLE_ROUTE = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), os.environ.get("INTENT_MANAGERS_CACHE_ROUTE"))
print("Find cache at: " + str(BASE_PICKLE_ROUTE))
BIG_HELP_FILE = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "helpfiles/help.md")
ARG_HELP_FILE = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "helpfiles/arghelp.md")
COMM_HELP_FILE = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "helpfiles/commhelp.md")
PROP_HELP_FILE = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "helpfiles/prophelp.md")
DPROP_HELP_FILE = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "helpfiles/dprophelp.md")
DARG_HELP_FILE = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "helpfiles/darghelp.md")
DCOMM_HELP_FILE = os.path.join(os.path.abspath(
    os.path.dirname(__file__)), "helpfiles/dcommhelp.md")


GENERIC_NO_ENTENDER = "Perdón, el chatbot no entendió su pregunta. Si no sabe cómo seguir, escriba: \'Ayuda\'"
ARGUMENT_INTENTS = {
    "Argumentos",
    "DetalleArgumentos",
    "DetalleArgumento",
    "ArgumentosComentario",
}
DOCACHE = False
"""
Este modulo contiene las llamadas a la lógica de todos los intent a procesar. 
Se delegan ciertas actividades a módulos y clases externas para abreviar el código.
"""

""" Se tiene que añadir un parámetro especial, Filtros, que es uno cuyo valor
es un criterio de búsqueda. Se usa para casos como "Propuestas por temas" , 
donde se pregunta clasificar por un criterio pero no se dan los valores para hacer el filtrado.
Así, si se pregunta algo como "Propuestas del barrio de Chamartín por temas y por categoria", daría
Filtros = ["temas","categorias"], 
barrios = ["Chamartín"] """
expectedparameters = df_request.expectedcriterios + [
    "Filtros",
]

"""
Este diccionario mapea los parametros/criterios de busqueda con las respectivas tablas de la DB,
y con el valor a comprobar para su existencia. También se facilita una lambda que puede modificar 
la entrada dada por el usuario para normalizarla a como debe aparecer en la DB. Por ejemplo, si
el usuario introduce "Urbanismo", no encontrará el topic "urbanismo" pero con la lambda facilitada ya sí.
"""
mappingToDB = {
    "categorias": (CatCategories, "name", lambda val: quitar_tildes(val).replace('"', '').replace("'", "").capitalize()),
    "temas": (CatTopics, "topic", lambda val: quitar_tildes(val).replace('"', '').replace("'", "").casefold()),
    "distritos": (GeoDistricts, "name", lambda val: quitar_tildes(val).replace('"', '').replace("'", "").capitalize()),
    "barrios": (GeoNeighborhoods, "name", lambda val: quitar_tildes(val).replace('"', '').replace("'", "").capitalize()),
    "localizaciones": (GeoStreets, "street", lambda val: quitar_tildes(val).replace('"', '').replace("'", "").lower()),
}


def ordenar_resultados(query, valores, entity=Proposals):

    ordenes = []
    reverse = False
    for orden in valores:
        if "ordenfecha" == orden and entity == Proposals:
            ordenes.append(Proposals.date)
        elif "ordenfecha" == orden and entity == ProposalComments:
            ordenes.append(ProposalComments.date)
        if "ordenvotos" == orden and entity == Proposals:
            ordenes.append(Proposals.numsupports)
        elif "ordenvotos" == orden and entity == ProposalComments:
            ordenes.append(ProposalComments.numpositivevotes -
                           ProposalComments.numnegativevotes)

        elif "ordencontroversia" == orden:
            if entity == Proposals:
                ordenes.append(MetricsControversy.value)
            elif entity == CatTopics:
                ordenes.append(MetricsTopicControversy.value)
        elif "ordeninverso" == orden:
            reverse = True
    if reverse:
        ordenes.reverse()
        for val in ordenes:
            query = query.order_by(asc(val))

    else:
        for val in ordenes:
            query = query.order_by(desc(val))
    if entity == Proposals:
        return query
    return query


def nextcriterio(prevcriterio: int, yapreguntados: list) -> Tuple[int, List[int]]:
    """
    Dado el criterio anteriormente preguntado,
    da el siguiente de los que el usuario aún no
    ha especificado o no ha querido especificar

    Trabaja en modo cola circular, devolviendo el siguiente de la
    lista "expectedcriterios" que no haya sido "yapreguntado", es
    decir, cuyo índice no haya sido
    marcado con "1" en la lista input "yapreguntados"

    Args:
        prevcriterio (int): Último criterio preguntado
        yapreguntados (list): Criterios ya preguntados

    Returns:
        Tuple[int, List[int]]: se devuelve el siguiente criterio a
        preguntar (posición 0) y los criterios ya preguntados actualizados
    """
    nuevospreguntados = yapreguntados.copy()
    

    if prevcriterio == -1:
        prevcriterio = 0
    else:
        nuevospreguntados[prevcriterio] = 1


    vueltas = 0
    while nuevospreguntados[prevcriterio] == 1:
        prevcriterio = (prevcriterio + 1) % len(df_request.expectedcriterios)
        vueltas += 1
        if vueltas == len(df_request.expectedcriterios) + 1:
            break
    return prevcriterio, nuevospreguntados


def mostrar_criterio(critStr: str):
    """
    Muestra el criterio especificado en un formato legible en lenguaje
    natural para el usuario para que introduzca los valores esperados.
    Es necesario para valores concretos de "Filtros"

    Args:
        critStr (str): Criterio identificado por su string ("barrios")

    Returns:
        str: Cadena de texto con info mejorada para el usuario
    """
    if critStr == "fromfecha":
        return "*desde una fecha* concreta (Introduce *más tarde* en formato: _DD/MM/AAAA_)"
    elif critStr == "tofecha":
        return "*hasta una fecha* concreta (Introduce *más tarde* en formato: _DD/MM/AAAA_)"
    else:
        return "por " + critStr


class UnexpectedChatId(Exception):
    def __init__(self, input_id, expected_id):
        self.input_id = input_id
        self.expected_id = expected_id

    def __str__(self):
        return (
            "Expected chat id: "
            + self.expected_id
            + ", but received: "
            + self.expected_id
        )


class IntentManager:
    """
    Clase que define un manejador de la situación conversacional con un
    usuario identificado con su chat_id de Telegram o bien con alguien usando
    la consola de DialogFlow.

    El soporte completo se consigue en Telegram, eso sí. El chat_id es un id que
    genera esa aplicación para cada usuario cuando se conecta con el
    bot https://t.me/chat_tfg_coll_bot. El mapeo chat_id a IntentManager
    se hace en __init__.py, en la parte del servidor webhook.

    Raises:
        UnexpectedChatId: Excepción para el caso que el id haya podido cambiar
        en mitad de una conversación ya mapeada en el sistema
    """

    class Preguntas:
        """
        Clase que implementa preguntas posibles al usuario

        """

        criterioEsperado = -1

        def preguntarCriterio(
            self, criterio: int, aclaracion: str = ""
        ) -> DialogflowResponse:
            """
            Pregunta al usuario si quiere filtrar por un criterio concreto
            (identificado por su índice en la lista "expectedcriterios")

            Args:
                criterio (int): Indice de criterio
                aclaracion (str, optional): Aclaración inicial para casos
                que se quiera modificar el comienzo de la pregunta. Defaults to "".

            Returns:
                DialogflowResponse: Respuesta de dialogflow en objeto
            """
            self.criterioEsperado = criterio
            return DFresponse(
                fulfillment_message=aclaracion
                + "¿Quieres filtrar "
                + mostrar_criterio(df_request.expectedcriterios[criterio])
                + "?"
            )

        def informarSobreCriteriosPedidos(self, params: dict):
            """
            Informa de criterios ya indicados por el usuario

            Args:
                params (dict): Diccionario de la forma:
                - clave: Nombre de criterio
                - valor: Valor/es de criterio

            Returns:
                DialogflowResponse: Respuesta de dialogflow en objeto
            """
            filtros = ""
            for k, v in params.items():
                filtros += "- {} = {}\n".format(
                    k, quitar_tildes(v).replace("'", '').replace('"', ''))
            return DFresponse(
                fulfillment_message="Se va a proceder a buscar propuestas con estos parámetros de búsqueda (filtros):\n"
                + filtros
                + "\n"
                + "¿Quiere especificar más filtros? \[_Sí/No/Cancelar_\]"
            )

        def reset(self):
            """
            Resetea el estado de esta clase interna (el índice del criterio
            que esperamos del usuario). Si es -1, se preguntará el primero disponible
            según la función nextcriterio
            """
            self.criterioEsperado = -1

        def informarValorNoEncontrado(
            self, criterio: int, valor: Any
        ) -> DialogflowResponse:
            return DFresponse(
                fulfillment_message="No se encuentra el valor: _"
                + str(valor)
                + "_ dentro de la colección de *"
                + df_request.expectedcriterios[criterio]
                + "*. Por favor, especifica otro o responde que no importa para descartarlo"
            )

    def __init__(self, dfr: DFrequest) -> None:
        """
        Constructor de un Intent Manager

        Args:
            dfr (DFrequest): Objeto con información
            parseada de la Request recibida del servidor de DialogFlow
        """
        self.id = dfr.chat_id
        self.args = None
        self.last_query = None
        self.partial_result = None
        self._last_comment_id = None
        self.criteriosSeleccionados = dict()
        self.yapreguntados = [0] * len(df_request.expectedcriterios)
        self.last_arguments_comments_user_question = None
        self.asker = IntentManager.Preguntas()
        self.already_joinedLocations = False
        self.last_results = {
            "Propuestas": None,
            "Categorias": None,
            "Comentarios": None,
            "Argumentos": None,
            "Temas": None,
            "Logs": None,
            "Barrios": None,
            "Distritos": None
        }
        self.last_index = 0
        self.count = 0
        self.from_files = True
        self.reset()
        self._reset_get_whatever_params()

    def save_last_results(self, dfr, tipo, listemas):
        try:
            f = open(BASE_PICKLE_ROUTE + '/' + str(tipo) +
                     '/' + str(dfr.chat_id), "wb+")
        except:
            try:
                os.makedirs(BASE_PICKLE_ROUTE + '/' + str(tipo) + '/')
            except:
                pass
            f = open(BASE_PICKLE_ROUTE + '/' + str(tipo) +
                     '/' + str(dfr.chat_id), "wb+")

        pickle.dump(listemas, f)
        self.last_results[str(tipo)] = None

    def _getwhatever(
        self,
        dfr: DFrequest,
        temaCatProp: str,
        initializer: Callable,
        writer: Callable[[Any], str],
        max_limit: int,
        with_numbers: bool = True,
        next=False,
        dont_over_look=False,
        aclaracion=""
    ) -> str:
        """
        Método auxiliar que gestiona casos en los que los resultados obtenidos
        son una lista demasiado larga para ser mostrada de golpe en una única
        respuesta del chatbot.

        Esto es necesario porque el Webhook no permite mensajes demasiado largos
        y puede pasar que no termine de procesar la propuesta por timeouts

        Args:
            dfr (DFrequest): Request recibida
            temaCatProp (str): Valor con el que direccionar la lista larga obtenida
            en el contexto de este IntentManager (self.last_results[temaCatProp])
            initializer (Callable): Lambda que inicialiaza la lista larga.
            TODO necesita quizá ir haciendo "yields" mejor.
            writer (Callable[[Any], str]): Función que se utilizará para
            mostrar de forma "bonita" cada elemento de la lista larga
            max_limit (int): Máximo número de resultados por respuesta
            next (bool, optional): Si está a true, seguirá dando los
            siguientes resultados, discriminando los demás inputs. Defaults to False.

        Returns:
            str: Respuesta final del chatbot
        """
        extra_context = list()
        if temaCatProp == 'Logs':
            self.last_model = Logs
        elif temaCatProp == 'Propuestas':
            self.last_model = Proposals
        elif temaCatProp == 'Argumentos':
            extra_context.append("Argumentos-followup")
            self.last_model = Arguments
        elif temaCatProp == 'Commentarios':
            extra_context.append("Argumentos-followup")
            self.last_model = ProposalComments
        elif temaCatProp == 'CommentariosBY':
            extra_context.append("Argumentos-followup")
            self.last_model = ProposalComments
        elif temaCatProp == 'ArgumentosBY':
            extra_context.append("Argumentos-followup")
            self.last_model = ProposalComments
        elif temaCatProp == 'Temas':
            self.last_model = CatTopics
        botones = []
        extraopciones = ""
        if not next and temaCatProp is not None:
            self._last_temaCatProp = temaCatProp
        if "Argumentos" in self._last_temaCatProp or "Comentarios" in self._last_temaCatProp or "Propuestas" in self._last_temaCatProp:
            if not dont_over_look:
                botones.append([{
                    "text": "Ordenar {} por controversia".format("Argumentos" if "Argumentos" in self._last_temaCatProp else "Comentarios" if "Comentarios" in self._last_temaCatProp else "Propuestas"),
                    "callback_data": "Ordenar por controversia"
                }])
            extra_context.append("Argumentos-followup")
        if "Argumentos" in self._last_temaCatProp and not dont_over_look:
            botones.append([{
                "text": "Agrupar por intención",
                "callback_data": "Argumentos por intención"
            }])
            extra_context.append("Argumentos-followup")
        if "Comentarios" in self._last_temaCatProp or "Propuestas" in self._last_temaCatProp:
            botones.append([{
                "text": "{} por votos".format("Comentarios" if "Comentarios" in self._last_temaCatProp else "Propuestas"),
                "callback_data": "Ordenar por votos"
            }])
            extra_context.append("Argumentos-followup")
        if "Propuestas" in self._last_temaCatProp:
            botones.append([{
                "text": "Más recientes primero",
                "callback_data": "Ordenar por fecha"
            }, {
                "text": "Más antiguas primero",
                "callback_data": "Ordenar por fecha ascendente"
            }
            ])
            extraopciones = "\n-'`Argumentos/Comentarios/Detalle de la propuesta numero 4`' (número *4)* del índice),\n-'`Argumentos/Comentarios/Detalle de la propuesta con id 486`' (486, como donde se dice en *(pid: 486)*)\n-'`Comentarios de las propuestas anteriores`',\n-'`Argumentos de las propuestas anteriores`'" if dfr.withargs else "\n-'`Comentarios/Detalle de la propuesta numero 4`' (número *4)* del índice),\n-'`Comentarios/Detalle de la propuesta con id 486`' (486, como donde se dice en *(pid: 486)*)\n-'`Comentarios de las propuestas anteriores`'"

            vercomsargs = [{
                "text": "Comentarios" if not dont_over_look else "Comentarios (todos)",
                "callback_data": "Comentarios de las propuestas anteriores"
            }]
            if dfr.withargs:
                vercomsargs.append({
                    "text": "Argumentos" if not dont_over_look else "Argumentos (todos)",
                    "callback_data": "Argumentos de las propuestas anteriores"
                })
            botones.append(vercomsargs)

        elif "Comentarios" in self._last_temaCatProp:
            if dont_over_look:
                extraopciones = "\n-'`Ver comentario con id 228`' (228, o los que salgan en los resultados como *C<id>*)"
            else:
                extraopciones = "\n-'`Comentarios que contengan \"texto\"`',\n-'`Ver comentario con id 228`' (228, o los que salgan en los resultados como *C<id>*)"

            if dfr.withargs and not dont_over_look:
                extraopciones += "\n(Lo mismo para argumentos, con `\"Ver argumento *A<id>*\"` por ejemplo)"
                botones.append([{
                    "text": "Argumentos",
                    "callback_data": "argumentos"
                }, {
                    "text": "Resumen resultados",
                    "callback_data": "comentarios"
                },

                ])
                botones.append([{
                    "text": "Mostrar con los argumentos",
                    "callback_data": "ver argumentos y comentarios"
                }])
        elif "Argumentos" in self._last_temaCatProp:
            if dont_over_look:
                extraopciones = "\n-'`Ver argumento/comentario con id 228`' (228, o los que salgan en los resultados como *A<id>*/*C<id>*),\n-'`Argumentos que traten de \"Madrid\"`',\n-'`Argumentos de tipo \"contraste\"`"
            else:
                extraopciones = "\n-'`Argumentos/comentarios que contengan \"texto\"`',\n-'`Ver argumento/comentario con id 228`' (228, o los que salgan en los resultados como *A<id>*/*C<id>*),\n-'`Argumentos que traten de \"Madrid\"`',\n-'`Argumentos de tipo \"contraste\"`"
            if not dont_over_look:
                botones.append([{
                    "text": "Resumen resultados",
                    "callback_data": "argumentos"
                }, {
                    "text": "Comentarios",
                    "callback_data": "comentarios"
                },

                ])
                botones.append([{
                    "text": "Mostrar con los comentarios",
                    "callback_data": "ver argumentos y comentarios"
                }])
        if "Temas" in self._last_temaCatProp:
            botones.append([{
                "text": "Ordenar por controversia",
                "callback_data": "ordenar por controversia"
            }])

        if not next:
            listtemas, self.last_query = initializer()
            self._last_max_limit = max_limit
            self._last_temaCatProp = quitar_tildes(temaCatProp)
            self._last_with_numbers = with_numbers
            self._last_writer = writer
            self.last_index = 0

            self.save_last_results(dfr, temaCatProp, listtemas)
            self.count = len(listtemas)
            if self.count == 0:
                self._reset_get_whatever_params()
                return dfr.addContexts(DFresponse(
                    aclaracion+"No se encontraron {} para mostrar con los criterios pedidos.".format(
                        quitar_tildes(temaCatProp).lower()
                    )
                ), extra_context).get_final_response(dfr)

        if (self.last_index + 1) * self._last_max_limit < self.count:
            lt = "Mostrando resultados ({} de {}):\n\n{}\n\n".format(
                self._last_max_limit * (self.last_index + 1),
                self.count,
                list_to_telegram(
                    self.get_last_results(dfr, self._last_temaCatProp)[
                        self.last_index
                        * self._last_max_limit: (self.last_index + 1)
                        * self._last_max_limit
                    ],
                    self._last_writer,
                    offset=self.last_index * self._last_max_limit,
                    with_numbers=self._last_with_numbers
                ),
            )
            self.last_index += 1
            botones.insert(0,
                           [
                               {
                                   "text": "Ver más",
                                   "callback_data": "Siguiente"
                               },
                               {
                                   "text": "Salir",
                                   "callback_data": "Salir"
                               }
                           ],
                           )
            extra_context.append("more")
            return dfr.addContexts(DFresponse(aclaracion+lt, botones=botones, extra_opciones=extraopciones), extra_context).get_final_response(dfr)
        elif next:
            lt = "Últimos resultados:\n\n{}".format(
                list_to_telegram(
                    self.get_last_results(dfr, self._last_temaCatProp)[
                        self.last_index * self._last_max_limit: self.count
                    ],
                    self._last_writer,
                    offset=self.last_index * self._last_max_limit,
                    with_numbers=self._last_with_numbers
                )
            )
            self.last_index = 0
            return dfr.addContexts(DFresponse(aclaracion+lt, botones=botones, extra_opciones=extraopciones), extra_context).get_final_response(dfr)

        else:
            self.last_index = 0
            lt = "{}".format(
                list_to_telegram(
                    self.get_last_results(
                        dfr, self._last_temaCatProp),
                    self._last_writer,
                    with_numbers=self._last_with_numbers
                )
            )
            return dfr.addContexts(DFresponse(fulfillment_message=aclaracion+lt, botones=botones, extra_opciones=extraopciones), extra_context).get_final_response(dfr)

    def get_last_results(self, dfr: DFrequest, tipo: str):
        try:
            f = open(BASE_PICKLE_ROUTE + '/' + str(tipo) +
                     '/' + str(dfr.chat_id), "rb")
            self.last_results[str(tipo)] = pickle.load(f)
        except FileNotFoundError as e:
            print(e)
            pass

        return self.last_results.get(tipo)

    def _call_intent(self, intent: str, dfr: DFrequest):
        """
        Función que realiza las llamadas a los métodos que gestionan
        cada intent en base al que se indica en la request recibida

        Args:
            intent (str): Intent requerido
            dfr (DFrequest): Request recibida

        Raises:
            UnexpectedChatId: Si el chat_id no coincide con el que se
            generó este IntentManager

        Returns:
            str: Respuesta de dialogflow en cadena de texto
        """
        if dfr.chat_id != self.id:
            raise UnexpectedChatId(dfr.chat_id, self.id)
        if dfr.withargs is False:
            if dfr.intent in ARGUMENT_INTENTS:
                logs.write_log(int(dfr.chat_id), intent="INTENT_INVALID", activity={'INTENT_INVALID'}, ts=datetime.now(
                ), input=dfr.text, response=GENERIC_NO_ENTENDER, observaciones="misuse", withargs=dfr.withargs)
                return dfr.addContexts(DialogflowResponse(GENERIC_NO_ENTENDER), contexts=dfr.outputContextsNames).get_final_response()
        try:
            return getattr(IntentManager, intent.lower())(self, dfr)
        except Exception as e:
            tb = str(traceback.format_exc())
            print(tb)
            logs.write_log(int(dfr.chat_id), intent=dfr.intent, activity={dfr.intent}, ts=datetime.now(
            ), input=dfr.text, response=str(traceback.format_exc()), observaciones="EXCEPTION", withargs=dfr.withargs)
            return DFresponse(
                "\[ERROR] Lo sentimos, ocurrió un error inesperado. (Para desarrolladores, hágales llegar este mensaje: _{}_)".format(
                    str(traceback.format_exc()).replace('_', '__')
                )
            ).get_final_response(dfr)

    def _addcriterio(self, dfr: DFrequest):
        """
        Añade un criterio y su valor de filtrado a los
        "self.criteriosSeleccionados", que luego se utilizarán
        para realizar la query de búsqueda en la función
        self._ejecutar_busqueda. El valor de filtrado
        se obtiene de los resultados de la request recibida

        Args:
            dfr (DFrequest): Request recibida
        """
        valoresEsperados = dfr.get_allparameters()["valorespreguntados"]
        print(
            'Añadido criterio de búsqueda: "'
            + df_request.expectedcriterios[self.asker.criterioEsperado]
            + '" con valor/es: '
            + str(valoresEsperados)
            + "",
            file=stderr,
        )
        self.criteriosSeleccionados.update(
            {df_request.expectedcriterios[self.asker.criterioEsperado]                : valoresEsperados}
        )

    def _selectvia(self, criterioString: str, valores: list) -> None:
        """
        Añade a la query un filtrado por el criterio y los valores
        indicados

        Args:
            criterioString (str): criterio
            valores (list): valores de filtrado
        """
        if not self.already_joinedLocations and criterioString in [
            "localizaciones",
            "distritos",
            "barrios",
        ]:
            # No permite hacer joins con la misma tabla varias veces...
            self.already_joinedLocations = True
            self.partial_result = self.partial_result.join(
                ProposalLocations, ProposalLocations.id == Proposals.id
            )

        if criterioString == "temas":
            self.partial_result = self.partial_result.join(
                ProposalTopics, ProposalTopics.id == Proposals.id
            ).filter(
                or_(
                    ProposalTopics.topic.like(
                        "%{}%".format(quitar_tildes(valor).replace("'", '').replace('"', '').casefold()))
                    for valor in valores
                )
            )
        elif criterioString == "barrios":
            self.partial_result = self.partial_result.filter(
                or_(
                    ProposalLocations.neighborhood.like(
                        "%{}%".format(quitar_tildes(valor).replace(
                            "'", '').replace('"', '').capitalize())
                    )
                    for valor in valores
                )
            )
        elif criterioString == "categorias":

            self.partial_result = self.partial_result.join(
                ProposalCategories, ProposalCategories.id == Proposals.id
            ).filter(
                or_(
                    ProposalCategories.category.like(
                        "%{}%".format(quitar_tildes(valor).replace(
                            "'", '').replace('"', '').capitalize())
                    )
                    for valor in valores
                )
            )
        elif criterioString == "distritos":
            self.partial_result = self.partial_result.filter(
                or_(
                    ProposalLocations.district.like(
                        "%{}%".format(quitar_tildes(valor).capitalize())
                    )
                    for valor in valores
                )
            )
        elif criterioString == "localizaciones":
            self.partial_result = self.partial_result.filter(
                or_(
                    ProposalLocations.location.like(
                        "%{}%".format(quitar_tildes(valor).casefold())
                    )
                    for valor in valores
                )
            )
        elif criterioString == "texto":
            self.partial_result = self.partial_result.filter(
                or_(Proposals.summary.contains(quitar_tildes(valor))
                    for valor in valores)
            )

        elif criterioString == "titulo":
            self.partial_result = self.partial_result.filter(
                or_(Proposals.title.contains(quitar_tildes(valor))
                    for valor in valores)
            )
        elif criterioString == "fromfecha":
            self.partial_result = self.partial_result.filter(
                or_(
                    Proposals.date >= datetime.strptime(valor, "%d/%m/%Y")
                    for valor in valores
                )
            )
        elif criterioString == "tofecha":
            self.partial_result = self.partial_result.filter(
                or_(
                    Proposals.date <= datetime.strptime(valor, "%d/%m/%Y")
                    for valor in valores
                )
            )
        elif criterioString == "orden":
            self.partial_result = ordenar_resultados(
                self.partial_result, valores)

    def respuestafiltro(self, dfr: DFrequest) -> str:
        """
        Gestiona el intent RespuestaFiltro, followup de Filtros. Se usa para
        preguntar al usuario qué valores de filtrado usar para el criterio
        una vez ha indicado éste si quiere filtrar por él o no

        Args:
            dfr (DFrequest): Request recibida de DialogFlow

        Returns:
            str: Respuesta para DialogFlow en cadena
        """
        if dfr.parameters.get("YesORNoORCancel") == "Yes":

            resp = DFresponse(
                fulfillment_message="Vale, introduce ahora qué valor del criterio anterior ({})".format(
                    mostrar_criterio(df_request.expectedcriterios[self.asker.criterioEsperado]))
                + " tener en cuenta para la búsqueda de propuestas. {}".format(" Valores esperados: {}".format("".join(["- " + str(t.topic)+"\n" for t in CatTopics.query.filter(CatTopics.category.in_([quitar_tildes(c).capitalize() for c in self.criteriosSeleccionados.get(
                    'categorias')])).all()])) if df_request.expectedcriterios[self.asker.criterioEsperado] == "temas" and self.criteriosSeleccionados.get('categorias') is not None and len(self.criteriosSeleccionados.get('categorias')) > 0 else "")
            )

            dfr.addContexts(
                resp,
                [
                    "seguirfiltrando-followup",
                    "Select-followup",
                    "propuestas",
                    "respuestapreguntacriterio-followup",
                ],
            )
            return resp.get_final_response(dfr)

        elif dfr.parameters.get("YesORNoORCancel") == "Cancel":
            self.reset()
            resp = DFresponse(
                fulfillment_message='De acuerdo, por favor formula otra petición (recuerda: escribe "ayuda" o similar para obtener una guía breve de uso de este chatbot'
            )
            dfr.addContexts(resp, [])
            return resp.get_final_response(dfr)
        elif dfr.parameters.get("YesORNoORCancel") == "No":
            return self.filtros(dfr, seguir=True)
        elif dfr.parameters.get("YesORNoORCancel") == "Ejecutar":
            return self._ejecutar_busqueda(dfr, aclaracion="")
        else:
            resp = DFresponse(
                fulfillment_message="\[ERROR] No entendí, lo siento, escribe '_Sí_' para introducir el criterio, '_No_' para dejarlo o '_Cancelar_' para abandonar la petición. O bien escribe '_Ejecutar_' para ejectuar ya la búsqueda"
            )
            return dfr.addContexts(
                resp,
                ["seguirfiltrando-followup", "Select-followup", "propuestas"],
            ).get_final_response(dfr)

    def filtros(self, dfr: DFrequest, seguir=False) -> str:
        """
        Gestiona el intent Filtros, que se usa para preguntar al usuario si quiere
        modificar los criterios de búsqueda

        Args:
            dfr (DFrequest): Request de entrada
            seguir (bool, optional): Si se pone a true, no hará la pregunta
            y preguntará directamente los valores del siguiente criterio
            Solo para casos muy concretos es necesario. Defaults to False.

        Returns:
            str: Respuesta para DialogFlow en cadena
        """
        if "YesORNoORCancel" not in dfr.parameters.keys() and seguir == False:
            resp = DFresponse(
                fulfillment_message='[ERROR] No entendí, lo siento, responde "_Sí_" para continuar estableciendo criterios de búsqueda, "_No_" para ejecutarla y "_Cancelar_" para introducir otra petición'
            )
            resp = dfr.addContexts(
                resp, ["propuestas", "Select-followup",
                       "seguirfiltrando-followup"]
            )
        elif dfr.parameters.get("YesORNoORCancel") == "Yes" or seguir == True:
            self.asker.criterioEsperado, self.yapreguntados = nextcriterio(
                self.asker.criterioEsperado, self.yapreguntados
            )
            print("Asked criteria: ")
            print(self.yapreguntados)
            if sum(self.yapreguntados) >= len(df_request.expectedcriterios):
                # Hemos preguntado por todos los posibles criterios y procedemos a la búsqueda.
                return self._ejecutar_busqueda(
                    dfr,
                    aclaracion="No hay más criterios (se han incluido todos los pedidos hasta ahora) y se muestran los resultados ahora: ",
                )
            else:
                resp = self.asker.preguntarCriterio(
                    self.asker.criterioEsperado, aclaracion="De acuerdo. "
                )
                resp = dfr.addContexts(
                    resp, ["propuestas", "Select-followup",
                           "seguirfiltrando-followup"]
                )
        elif dfr.parameters.get("YesORNoORCancel") == "Cancel":
            self.reset()
            resp = DFresponse(
                fulfillment_message='De acuerdo, por favor formula otra petición (recuerda: escribe "_ayuda_" o similar para obtener una guía breve de uso de este chatbot'
            )
            resp = dfr.addContexts(resp, [])
        elif dfr.parameters.get("YesORNoORCancel") == "No":
            return self._ejecutar_busqueda(dfr)
        else:
            resp = DFresponse(
                fulfillment_message='[ERROR] No entendí, lo siento, responde "Sí" para continuar estableciendo criterios de búsqueda, "No" para ejecutarla y "Cancelar" para introducir otra petición'
            )
            resp = dfr.addContexts(
                resp, ["propuestas", "Select-followup",
                       "seguirfiltrando-followup"]
            )
        return resp.get_final_response(dfr)

    def comprobarvalor(self, dfr: DFrequest) -> str:
        """
        Gestiona el Intent ComprobarValor.

        Comprueba el valor o valores introducidos por el usuario en el intent
        RespuestaFiltro.

        Args:
            dfr (DFrequest): Request input

        Returns:
            str: Respuesta para DialogFlow en cadena
        """
        valoresEsperados = dfr.get_allparameters()["valorespreguntados"]

        criterioString = df_request.expectedcriterios[self.asker.criterioEsperado]
        if (
            criterioString == "texto"
            or criterioString == "title"
        ):
            self._addcriterio(dfr)
        elif criterioString == "tofecha" or criterioString == "fromfecha":
            for v in valoresEsperados:
                if not re.match(r"(0[1-9]|[12][0-9]|3[01])\/(0[1-9]|1[0-2])\/\d{4}", v):
                    return dfr.addContexts(
                        DFresponse(
                            fulfillment_message="\[ERROR] La fecha dada: "
                            + v
                            + ", no se corresponde con el formato esperado (_DD/MM/AAAA_) "
                        ),
                        [
                            "propuestas",
                            "Select-followup",
                            "seguirfiltrando-followup",
                            "respuestapreguntacriterio-followup",
                        ],
                    ).get_final_response(dfr)
                else:
                    try:
                        datetime.strptime(v, "%d/%m/%Y")
                    except Exception():
                        return dfr.addContexts(
                            DFresponse(
                                fulfillment_message="\[ERROR] La fecha dada: "
                                + v
                                + ", no es posible, por favor revisa que es válida "
                            ),
                            [
                                "propuestas",
                                "Select-followup",
                                "seguirfiltrando-followup",
                                "respuestapreguntacriterio-followup",
                            ],
                        ).get_final_response(dfr)

            self._addcriterio(dfr)
        else:
            for v in valoresEsperados:

                if (
                    len(
                        list(
                            mappingToDB[criterioString][0]
                            .query.filter(
                                getattr(
                                    mappingToDB[criterioString][0],
                                    mappingToDB[criterioString][1],
                                ).like("%{}%".format(mappingToDB[criterioString][2](v)))
                            )
                            .limit(1)
                        )
                    )
                    < 1
                ):
                    return dfr.addContexts(
                        self.asker.informarValorNoEncontrado(
                            self.asker.criterioEsperado, v
                        ),
                        [
                            "propuestas",
                            "Select-followup",
                            "seguirfiltrando-followup",
                            "respuestapreguntacriterio-followup",
                        ],
                    ).get_final_response(dfr)

            self._addcriterio(dfr)
        return dfr.addContexts(
            self.asker.informarSobreCriteriosPedidos(
                self.criteriosSeleccionados),
            ["propuestas", "Select-followup"],
        ).get_final_response(dfr)

    def _ejecutar_busqueda(self, dfr: DFrequest, aclaracion="", maxlimit=500) -> str:
        """
        Ejecuta la búsqueda final de propuestas,
        tras haber obtenido el beneplácito del usuario y mostrando
        la respuesta con un formato adecuado.

        Args:
            dfr (DFrequest): Request de entrada
            aclaracion (str, optional): Aclaración inicial antes de los
            resultados. Defaults to "".
            maxlimit (int, optional): Máximo limite de propuestas
            que mantener en el contexto para ir mostrando.
            Defaults to 500.
        """

        def initializer():
            if self.partial_result is None:
                self.partial_result = Proposals.query.with_entities(Proposals).join(
                    MetricsControversy,
                    MetricsControversy.proposalid == Proposals.id
                ).filter(
                    MetricsControversy.name == proposals.DEFAULT_CONTROVERSY
                )
            for criterio, valores in self.criteriosSeleccionados.items():
                print(
                    'SELECCIONANDO POR "'
                    + criterio
                    + '" con valor/es: '
                    + str(valores),
                    file=stderr,
                )
                if criterio != 'orden':
                    self._selectvia(criterio, valores)

            self.last_query_without_order = self.partial_result
            if self.criteriosSeleccionados.get("orden") is not None:
                self._selectvia(
                    "orden", self.criteriosSeleccionados.get("orden"))
            else:
                finalresult_query = self.partial_result.order_by(
                    desc(Proposals.numsupports)
                )
            finalresult_query = self.partial_result

            finalresult = finalresult_query.all()
            return finalresult, finalresult_query

        return self._getwhatever(
            dfr,
            "Propuestas",
            initializer,
            writer=lambda result: repr(result),
            max_limit=MAX_PROPUESTAS_PER_QUERY,aclaracion=aclaracion
        )

    def getpropuestas(self, dfr: DFrequest) -> str:
        """
        Gestiona el intent GetPropuestas.

        Obtiene las propuestas que diga el usuario, preguntando
        criterios extra si se ve necesario en base a varias condiciones

        Args:
            dfr (DFrequest): Request de entrada

        Returns:
            str: Respuesta de este intent
        """
        self.reset()
        self._reset_get_whatever_params()
        self.from_files = True
        self.set_args(dfr, None)

        self.partial_result = Proposals.query.with_entities(Proposals).join(
            MetricsControversy,
            MetricsControversy.proposalid == Proposals.id
        ).filter(
            MetricsControversy.name == proposals.DEFAULT_CONTROVERSY
        )

        criterios_y_tipos = dfr.get_allparameters(forproposals=True)
        self.criteriosSeleccionados = criterios_y_tipos.copy()

        if "Filtros" in criterios_y_tipos.keys():
            self.yapreguntados = [1] * len(self.yapreguntados)
            for c in criterios_y_tipos["Filtros"]:

                self.yapreguntados[
                    df_request.expectedcriterios.index(c)
                ] = 0  # ya preguntados todos los demás

            if sum(self.yapreguntados) < len(df_request.expectedcriterios):

                return self.filtros(dfr, seguir=True)
            else:
                return self._ejecutar_busqueda(dfr, aclaracion="Mostrando resultados.")
        print("Antes de... ") 
        print(self.criteriosSeleccionados)
        print(self.yapreguntados)
        for k in self.criteriosSeleccionados.keys():
            if k != 'orden':
                self.yapreguntados[df_request.expectedcriterios.index(k)] = 1
        print(self.yapreguntados)
        return self.asker.informarSobreCriteriosPedidos(
            self.criteriosSeleccionados
        ).get_final_response(dfr)

    def ordenar(self, dfr: DFrequest):
        ORDENES = ['ordencontroversia', 'ordenfecha',
                   'ordenvotos', 'ordeninverso']
        params = dfr.get_allparameters()

        def checkorderok(params):
            if "orden" in params.keys():
                if len(params.get('orden')) > 0:
                    for o in params.get('orden'):
                        if o not in ORDENES:
                            return False
                    return True
            return False

        if self.last_query is None:
            return DFresponse("\[ERROR] No has obtenido anteriormente nada que ordenar").get_final_response(dfr, observaciones="misuse")

        if checkorderok(params):
            if self.last_query == "Comentarios":
                dfr.parameters["orden"] = params["orden"]
                dfr.parameters['visualizar'] = 'ver'
                if len(self.get_last_results(dfr, "Comentarios") or ()) > 0 and self._last_comment_id is not None:
                    dfr.parameters['commby'] = "conid"
                    dfr.parameters['idcom'] = self._last_comment_id
                    self._last_temaCatProp = "Comentarios"
                    nose = self.action_on_something(
                        lambda c: self.comentarioscomentario(dfr), dfr, entity="C")
                    if type(nose) == DFresponse:
                        return nose.get_final_response(dfr)
                    else:
                        return nose
                return self.detallecomentarios(dfr)
            elif self.last_query == "Argumentos":

                dfr.parameters["orden"] = params["orden"]
                dfr.parameters['visualizar'] = 'ver'
                if len(self.get_last_results(dfr, "Comentarios") or ()) > 0 and self._last_comment_id is not None:
                    dfr.parameters['commby'] = "conid"
                    dfr.parameters['idcom'] = self._last_comment_id
                    self._last_temaCatProp = "Argumentos"
                    nose = self.action_on_something(
                        lambda c: self.argumentoscomentario(dfr), dfr, entity="C")
                    if type(nose) == DFresponse:
                        return nose.get_final_response(dfr)
                    else:
                        return nose
                return self.detalleargumentos(dfr)
            elif self.last_query_without_order is not None:
                def initializer():
                    result_query = ordenar_resultados(
                        query=self.last_query_without_order, valores=params["orden"], entity=self.last_model)

                    return result_query.all(), result_query
                return self._getwhatever(
                    dfr=dfr,
                    temaCatProp=self._last_temaCatProp,
                    initializer=initializer,
                    writer=self._last_writer,
                    max_limit=self._last_max_limit)
            else:
                return DFresponse("\[ERROR] No has obtenido anteriormente nada que ordenar").get_final_response(dfr, observaciones="misuse")
        else:
            return DFresponse("\[ERROR] El orden indicado no se reconoce. Prueba con estos: " + str(ORDENES)).get_final_response(dfr, observaciones="misuse")

    def reset(self):
        """
        Resetea el estado de esta conversación
        """
        self.asker.reset()
        self.partial_result = None
        self.unresolvedparameters = dict()
        self.yapreguntados = [0] * len(df_request.expectedcriterios)
        self.already_joinedLocations = False
        self.last_arguments_comments_user_question = None
        # Para mostrar muchos resultados de temas/categorias/propuestas
        self.last_index = 0
        self.count = 0

    def bighelp(self, dfr: DFrequest):
        """
        Gestiona el intent bighelp

        Se usa para devolver al usuario información general de ayuda
        cuando éste escribe algo como "Ayuda" o "Ayuda de propuestas/comm/args"

        Args:
            dfr (DFrequest): Request de entrada

        Returns:
            str: Respuesta para DialogFlow en cadena
        """

        help_file = open(BIG_HELP_FILE, "r")
        botones = [
            [{
                "text": "Ayuda de Propuestas",
                        "callback_data": "Ayuda de propuestas"
            },
            ],
            [{
                "text": "Ayuda de Comentarios",
                        "callback_data": "Ayuda de comentarios"
            }, {
                "text": "Ayuda de Argumentos",
                        "callback_data": "Ayuda de argumentos"
            }
            ] if dfr.withargs else [{
                "text": "Ayuda de Comentarios",
                "callback_data": "Ayuda de comentarios"
            }, ],
            [{
                "text": "Ayuda general",
                        "callback_data": "ayuda"
            }]
        ]

        if "detalle" in quitar_tildes(dfr.text.lower()) and "propuestas" in dfr.text.lower():
            help_file = open(DPROP_HELP_FILE, "r")
        elif "detalle" in quitar_tildes(dfr.text.lower()) and "argumentos" in dfr.text.lower():
            help_file = open(DARG_HELP_FILE, "r")
        elif "detalle" in quitar_tildes(dfr.text.lower()) and "comentarios" in dfr.text.lower():
            help_file = open(DCOMM_HELP_FILE, "r")
        elif "propuestas" in quitar_tildes(dfr.text.lower()):
            help_file = open(PROP_HELP_FILE, "r")
            botones.append([{
                "text": "Más sobre Propuestas",
                "callback_data": "Ayuda de DETALLEPROPUESTAS"
            }])
        elif "comentarios" in quitar_tildes(dfr.text.lower()):
            help_file = open(COMM_HELP_FILE, "r")
            botones.append([{
                "text": "Más sobre Comentarios",
                "callback_data": "Ayuda de DETALLECOMENTARIOS"
            }])
        elif "argumentos" in quitar_tildes(dfr.text.lower()):
            help_file = open(ARG_HELP_FILE, "r")
            botones.append([{
                "text": "Más sobre Argumentos",
                "callback_data": "Ayuda de DETALLEARGUMENTOS"
            }])

        help_file = help_file.read()
        if dfr.withargs:
            help_file: str = help_file.replace("ARGUMENTOS", "")
        else:
            help_file_l = [val for idx, val in enumerate(
                help_file.split("ARGUMENTOS")) if idx % 2 == 0]
            help_file = ""
            for v in help_file_l:
                help_file += v

        return dfr.addContexts(
            DFresponse(
                fulfillment_message=help_file,
                botones=botones
            ),
            dfr.outputContextsNames,
        ).get_final_response(dfr)

    def getbarrios(self, dfr: DFrequest):
        import yaml
        self.from_files = True
        self.set_args(dfr, None)

        def initializer():
            listtemas = GeoNeighborhoods.query.with_entities(GeoNeighborhoods).join(
                GeoDistricts, GeoDistricts.id == GeoNeighborhoods.districtid)
            if dfr.parameters.get("distritos") is not None:
                listtemas = listtemas.filter(
                    or_(
                        GeoDistricts.name.like(
                            "%{}%".format(quitar_tildes(c).replace("'", '').replace('"', '').capitalize()))
                        for c in dfr.parameters.get("distritos")
                    )
                )
            return listtemas.all(), listtemas

        return self._getwhatever(
            dfr,
            "Barrios",
            initializer,
            lambda barr: "{}".format(barr.name),
            proposals.MAX_TEMAS_PER_QUERY,
            aclaracion="En distrito/s:\n" + yaml.dump(dfr.parameters.get("distritos"), allow_unicode=True) +
            "se han obtenido estos barrios:\n\n" if len(
                dfr.parameters.get("distritos")) > 0 else ""
        )

    def gettemas(self, dfr: DFrequest):
        self.from_files = True
        self.set_args(dfr, None)

        def initializer():
            listtemas = CatTopics.query.with_entities(CatTopics).join(
                MetricsTopicControversy,
                MetricsTopicControversy.topic == CatTopics.topic).filter(
                    MetricsTopicControversy.name == proposals.DEFAULT_CONTROVERSY)
            
            if dfr.parameters.get("categorias") is not None:
                listtemas = listtemas.filter(
                    or_(
                        CatTopics.category.like(
                            "%{}%".format(quitar_tildes(c).replace("'", '').replace('"', '').capitalize()))
                        for c in dfr.parameters.get("categorias")
                    )
                )
            self.last_query_without_order = listtemas
            if 'ordencontroversia' == dfr.parameters.get("orden"):
                listtemas = ordenar_resultados(
                    listtemas, valores=['ordencontroversia'], entity=CatTopics)
            return listtemas.all(), listtemas

        return self._getwhatever(
            dfr,
            "Temas",
            initializer,
            lambda topic: "{} (cat: {})".format(topic.topic, topic.category),
            proposals.MAX_TEMAS_PER_QUERY,
        )

    def getmore(self, dfr: DFrequest):
        return self._getwhatever(dfr, None, None, None, None, next=True, dont_over_look=True)

    def _reset_get_whatever_params(self):
        self.last_index = 0
        self.count = 0
        self._last_writer = None
        self._last_temaCatProp = None
        self._last_max_limit = None
        self.last_query_without_order = None
        self.last_query = None

    def salirgetmore(self, dfr: DFrequest):
        """
        Gestiona el intent SalirGetMore

        Se usa cuando el usario no quiere ver más resultados de la
        lista larga que se estaba mostrando en ese momento

        Args:
            dfr (DFrequest): Request de entrada

        Returns:
            str: Respuesta de DialogFlow en cadena
        """
        self._reset_get_whatever_params()
        self.from_files = True
        self.set_args(dfr, None)
        return DFresponse("De acuerdo").get_final_response(dfr)

    def getcategorias(self, dfr: DFrequest):
        """
        Gestiona el intent GetCategorias

        Devuelve los categorias pedidas en base a lo que busca el usuario

        Args:
            dfr (DFrequest): Request de entrada

        Returns:
            str: Respuesta para DialogFlow en cadena
        """
        self.from_files = True
        self.set_args(dfr, None)

        def initializer():
            self.last_query_without_order = CatCategories.query
            return CatCategories.query.all(), CatCategories.query

        def writer(catacategory): return catacategory.name
        return self._getwhatever(
            dfr, "Categorias", initializer, writer, max_limit=MAX_CATEGORIAS_PER_QUERY
        )

    def getdistritos(self, dfr: DFrequest):
        """
        Gestiona el intent GetDistritos

        Devuelve los categorias pedidas en base a lo que busca el usuario

        Args:
            dfr (DFrequest): Request de entrada

        Returns:
            str: Respuesta para DialogFlow en cadena
        """
        self.from_files = True
        self.set_args(dfr, None)

        def initializer():
            self.last_query_without_order = GeoDistricts.query
            return GeoDistricts.query.all(), GeoDistricts.query

        def writer(dis): return dis.name
        return self._getwhatever(
            dfr, "Distritos", initializer, writer, max_limit=MAX_CATEGORIAS_PER_QUERY
        )

    def detallecomentarios(self, dfr: DFrequest):
        return self._aux_detalleComentariosArgumentos(dfr, tipo="C")

    def _aux_detalleComentariosArgumentos(self, dfr: DFrequest, tipo):

        args = self.get_args(dfr)
        if args is None:
            return self._aux_getcomentarios_argumentos(dfr, tipo)
            
        else:
            result = args.detalleComentarios(
                dfr) if tipo == "C" else args.detalleArgumentos(dfr)

            self.set_args(dfr, args)

            if callable(result):
                def lambdadef():
                    r = result()
                    self.set_args(dfr, args)
                    return r
                return self._getwhatever(
                    dfr,
                    temaCatProp="Comentarios" if tipo == "C" else "Argumentos",
                    initializer=lambdadef,
                    writer=lambda x: str(x),
                    max_limit=arguments.MAX_ARGS_PER_QUERY if tipo == "A" else comments.MAX_COMMENTS_PER_QUERY,
                    with_numbers=False)
            if self.last_arguments_comments_user_question is None:
                self.last_arguments_comments_user_question = dfr.text
            if type(result) == DFresponse:
                return result.get_final_response(dfr, "ok")
            if type(result[0]) == list:
                return self._getwhatever(
                    dfr,
                    temaCatProp="CommentariosBY" if tipo == "C" else "ArgumentosBY",
                    initializer=lambda: result,
                    writer=lambda x: str(x),
                    max_limit=MAX_ARGS_STATS_PER_QUERY if tipo == "A" else comments.MAX_COMMENT_STATS_PER_QUERY,
                    with_numbers=False)
            else:
                return dfr.addContexts(result[0], ["Argumentos-followup"]).get_final_response(dfr, "ok")

    def detalleargumentos(self, dfr: DFrequest):
        """
        Obtiene los argumentos en un arbol como si fuera con las
        propuestas y comentarios

        Args:
            dfr (DFrequest): Request de entrada

        Returns:
            str: Respuesta para DialogFlow en cadena
        """
        return self._aux_detalleComentariosArgumentos(dfr, tipo="A")

    def _aux_getcomentarios_argumentos(self, dfr: DFrequest, tipo: str):
        self.reset()
        self._reset_get_whatever_params()
        self.last_query = "Argumentos" if tipo == "A" else "Comentarios"
        args = Argumentos(dfr)
        self.args = args
        self.last_arguments_comments_user_question = dfr.text
        if dfr.parameters.get("propby") is not None and "sobrepropuestasanteriores" in dfr.parameters.get("propby"):
            resul = args.performArgSearch(
                self.get_last_results(dfr, "Propuestas"), tipo=tipo, withargs=dfr.withargs)
            self.args = args
        elif dfr.parameters.get("propby") is not None and "sobrepropuestaunica" in dfr.parameters.get("propby"):
            resul = args.performArgSearch(
                self.get_last_results(dfr, "Propuestas")[0], tipo=tipo, withargs=dfr.withargs)
            self.args = args
        elif dfr.parameters.get("propby") is not None or dfr.parameters.get("TipoBusqueda") is not None:
            def action_on_byprop(p: Proposals):
                self.reset_last_results(dfr)
                self.save_last_results(dfr, "Propuestas", [p, ])
                r = args.performArgSearch(
                    data=p, tipo=tipo, withargs=dfr.withargs)
                self.args = args
                return r

            def action_on_byprops(p: list):
                self.reset_last_results(dfr)
                self.save_last_results(dfr, "Propuestas", p)
                r = args.performArgSearch(
                    data=p, tipo=tipo, withargs=dfr.withargs)
                self.args = args
                return r

            def action_on_bytema(p: ProposalTopics):
                self.reset_last_results(dfr)
                r = args.performArgSearch(
                    data=p, tipo=tipo, withargs=dfr.withargs)
                self.args = args
                return r
            if "argspropuesta" in dfr.parameters.get("TipoBusqueda"):
                resul = self.action_on_proposal(action_on_byprop, dfr)
            elif "argscontemas" in dfr.parameters.get("TipoBusqueda"):
                resul = self.action_on_something(
                    action_on_bytema, dfr, entity="T")
            elif "sobrepropuestasanteriores" in (dfr.parameters.get("propby") or ()):
                resul = self.action_on_proposal(action_on_byprops, dfr)

            else:
                return DFresponse(
                    "\[ERROR] No se comprendió su petición de argumentos. Intenta reformularla como en los ejemplos",
                    extra_opciones="\n-`Argumentos sobre el tema \"urbanismo\"`\n-`Argumentos de la propuesta P7` (si sabe el *pid: 7* de la propuesta)\n-`Argumentos de la propuesta con titulo \"Limpiar las calles\"` (si sabe el *titulo* preciso de la propuesta)\n-`Argumentos de las propuestas anteriores` (si las acaba de listar tras escribir \"propuestas\" e ir filtrando)").get_final_response(dfr, observaciones="error")

        self.set_args(dfr, args)
        if type(resul) == DFresponse:
            return dfr.addContexts(resul, ['Argumentos-followup']).get_final_response(dfr, "ok")
        else:
            if type(resul[0]) == DFresponse:
                self.save_last_results(dfr, tipo=tipo, listemas=resul[1])
                return dfr.addContexts(resul[0], ['Argumentos-followup']).get_final_response(dfr, "ok")
            else:
                return self._getwhatever(dfr, temaCatProp="Comentarios" if tipo == "C" else "Argumentos", initializer=lambda: resul, writer=str, max_limit=arguments.MAX_ARGS_PER_QUERY if tipo == "A" else comments.MAX_COMMENTS_PER_QUERY, with_numbers=False)

    def argumentos(self, dfr: DFrequest) -> str:
        """
        Gestiona el intent Argumentos TODO

        Args:
            dfr (DFrequest): Request de entrada

        Returns:
            str: Respuesta para DialogFlow en cadena
        """
        return self._aux_getcomentarios_argumentos(dfr, tipo="A")

    def reset_last_results(self, dfr):
        for trait in set(self.last_results.keys()):
            self.save_last_results(dfr, trait, None)

    def getcomentarios(self, dfr: DFrequest):
        """
        Devuelve los comentarios desde una búsqueda de propuestas anterior (algo como
        ver comentarios de las propuestas anteriores, o comentarios de la última propuesta)

        Args:
            dfr (DFrequest): Request de dialogflow
        """
        return self._aux_getcomentarios_argumentos(dfr, tipo="C")

    def action_on_something(self, action, dfr: DFrequest, entity="P") -> DFresponse:
        if dfr.parameters.get("propby" if entity == "P" else "commby" if entity == "C" else "argby") is not None:
            if "sobrepropuestaunica" == dfr.parameters.get("propby" if entity == "P" else "commby" if entity == "C" else "argby") or "sobrepropuestaunica" in dfr.parameters.get("propby" if entity == "P" else "commby" if entity == "C" else "argby"):
                if self.get_last_results(dfr, "Propuestas") is None:
                    return DFresponse("\[ERROR] No hay propuestas anteriores o se ha perdido la última búsqueda, realízala de nuevo por favor")
                return action(self.get_last_results(dfr, "Propuestas")[0])
            elif "sobrepropuestasanteriores" == dfr.parameters.get("propby" if entity == "P" else "commby" if entity == "C" else "argby") or "sobrepropuestasanteriores" in dfr.parameters.get("propby" if entity == "P" else "commby" if entity == "C" else "argby"):
                if self.get_last_results(dfr, "Propuestas") is None:
                    return DFresponse("\[ERROR] No hay propuestas anteriores o se ha perdido la última búsqueda, realízala de nuevo por favor")
                return action(self.get_last_results(dfr, "Propuestas"))

        if dfr.parameters.get('idprop') == "":
            dfr.parameters['idprop'] = -1
        if dfr.parameters.get('idcom') == "":
            dfr.parameters['idcom'] = -1
        if dfr.parameters.get('idarg') == "":
            dfr.parameters['idarg'] = -1
        if entity == "P" and dfr.parameters.get('propby') is not None and dfr.parameters.get('propby') not in {"conid", "consid", "conindex"} and self.get_last_results(dfr, "Propuestas") is not None and len(self.get_last_results(dfr, "Propuestas")) > int(dfr.parameters.get('idprop') or -1):
            dfr.parameters['propby'] = "conindex"
        if dfr.parameters.get('propby' if entity == "P" else 'commby' if entity == "C" else 'argby') is None or dfr.parameters.get('propby' if entity == "P" else 'commby' if entity == "C" else 'argby') not in {"conid", "consid", "conindex"}:
            
            dfr.parameters['propby' if entity == "P" else 'commby' if entity ==
                           "C" else 'argby'] = 'conid' if entity == "P" else 'conid' if entity == "C" else 'conid'
        if dfr.parameters.get("sidprop"if entity == "P" else "sidcom" if entity == "C" else "sidarg") is not None:
            dfr.parameters["sidprop"if entity == "P" else "sidcom" if entity == "C" else "sidarg"] = quitar_tildes(dfr.parameters["sidprop"if entity ==
                                                                                                                                  "P" else "sidcom" if entity == "C" else "sidarg"].replace(' ', '').replace('"', '').replace("'", '').capitalize())

        if entity == "T":
            if (dfr.parameters.get("TipoBusqueda") is not None and "argscontemas" in dfr.parameters.get("TipoBusqueda")) or dfr.parameters.get("temas") is not None:
                ptopic = None
                try:
                    ptopic = ProposalTopics.query.filter(ProposalTopics.topic == quitar_tildes(
                        dfr.parameters.get("temas")).casefold()).all()[0]
                except IndexError as e:
                    if dfr.parameters.get("data") is not None:
                        ptopic = ProposalTopics.query.filter(ProposalTopics.topic == quitar_tildes(
                            dfr.parameters.get("data")[0]).casefold()).all()[0]
                    else:
                        print("Tema not found: " +
                              quitar_tildes(e), file=stderr)
                if ptopic is None:
                    return DFresponse("\[ERROR] No se ha encontrado el tema {}".format(dfr.parameters.get("temas")))
                return action(ptopic)

            else:
                return DFresponse("\[ERROR] No se ha reconocido un tema en tu pregunta")

        if dfr.parameters.get('propby' if entity == "P" else 'commby' if entity == "C" else 'argby') == "conindex" and (int(dfr.parameters.get("idprop" if entity == "P" else 'idcom' if entity == "C" else 'idarg') or -1) > 0):
            
            candidate = int(dfr.parameters.get(
                "idprop" if entity == "P" else 'idcom' if entity == "C" else 'idarg'))
            if self.get_last_results(dfr, "Propuestas" if entity == "P" else 'Comentarios' if entity == "C" else 'Argumentos') is not None:
                if (
                    candidate
                    > len(self.get_last_results(dfr, "Propuestas" if entity == "P" else 'Comentarios' if entity == "C" else 'Argumentos'))
                    or candidate < 1.0
                ):
                    return DFresponse(
                        "\[ERROR] El índice indicado es inválido, introduce otro"
                    )
                return action(
                    self.get_last_results(dfr, "Propuestas" if entity == "P" else 'Comentarios' if entity == "C" else 'Argumentos')[
                        int(candidate-1)
                    ]
                )
            else:

                return DFresponse("\[ERROR] Se han perdido las últimas propuestas buscadas, inicie una nueva búsqueda por favor")
        elif dfr.parameters.get("propby" if entity == "P" else "commby" if entity == "C" else "argby") == "conid" and int(dfr.parameters.get("idprop" if entity == "P" else "idcom" if entity == "C" else "idarg") or -1) > 0:
            candidate = int(
                dfr.parameters.get("idprop" if entity == "P" else "idcom" if entity == "C" else "idarg") or -1)

            thing = None
            try:
                thing = (Proposals if entity == "P" else ProposalComments if entity == "C" else Arguments).query.get(
                    int(candidate))
            except Exception as e:
                print(e, file=stderr)

            if thing is None:
                return DFresponse(
                    "\[ERROR] El elemento '{}' con id: ".format(
                        "propuesta" if entity == "P" else "comentario" if entity == "C" else "argumento")
                    + str(int(candidate))
                    + " no se ha encontrado"
                )
            return action(thing)
        elif dfr.parameters.get("propby" if entity == "P" else "commby" if entity == "C" else "argby") == "consid" and dfr.parameters.get("sidprop"if entity == "P" else "sidcom" if entity == "C" else "sidarg") != "":
            args = self.get_args(dfr)
            if args is None:
                return DFresponse("\[ERROR] Realiza antes una búsqueda compatible")
            else:
                if args.last_argCommentTree is None:
                    return DFresponse("\[ERROR] Para ver este el comentario con sid {} se necesita contexto, por favor, realiza una pregunta antes como \"Comentarios sobre la propuesta con id <id de propuesta>\"" .format(str(dfr.parameters.get("sidprop"if entity == "P" else "sidcom" if entity == "C" else "sidarg"))))

                found = args.get_something_by_sid(
                    str(dfr.parameters.get("sidprop"if entity == "P" else "sidcom" if entity == "C" else "sidarg")))
                if found is None:
                    return DFresponse("\[ERROR] No se encuentra el elemento con sid: {}" .format(str(dfr.parameters.get("sidprop"if entity == "P" else "sidcom" if entity == "C" else "sidarg"))))

                return action(found)
        elif (entity == "P" or entity == "A") and dfr.parameters.get("titulo") is not None and dfr.parameters.get("titulo") != "":
            try:
                proposal = Proposals.query.filter(
                    Proposals.title.like(
                        "%{}%".format(dfr.parameters.get("titulo"))
                    )
                ).all()[0]
            except IndexError as e:
                print(e, file=stderr)
                return (
                    "\[ERROR] La propuesta con titulo: "
                    + str(dfr.parameters.get("titulo"))
                    + " no se ha encontrado"
                )

            return action(proposal)
        self.set_args(dfr, None)
        return dfr.removeContexts(DFresponse(
            "\[ERROR] Faltan datos para poder obtener {} a la que te refieres".format("la propuesta" if entity == "P" else "el comentario" if entity == "C" else "el argumento")))

    def action_on_proposal(self, action, dfr: DFrequest):
        return self.action_on_something(action, dfr, entity="P")

    def detallepropuesta(self, dfr: DFrequest):
        args = self.get_args(dfr)
        if args is None:
            args = Argumentos(dfr)
            self.args = args

        def action(p):
            self.save_last_results(dfr, 'Propuestas', [p, ])
            self.save_last_results(dfr, 'Comentarios', None)
            self.save_last_results(dfr, 'Argumentos', None)
            args.performArgSearch(data=p, withargs=dfr.withargs)
            self.args = args
            return [args, proposals.detalle_propuesta(p, dfr.withargs)]

        val = self.action_on_proposal(action, dfr)
        if type(val) == list and len(val) == 2:
            args, ret = val
        else:
            ret = val
        self.set_args(dfr, args)
        return ret.get_final_response(dfr, "ok")

    def set_args(self, dfr, args: Argumentos):
        self.args = args

        if args is None:
            self.save_last_results(dfr, "ArgTrees", None)
            return
        if self.from_files:
            self.save_last_results(dfr, "ArgTrees", [
                (self.args.argCommentTree.proposals_all if self.args.argCommentTree is not None else None,
                 self.args.last_argCommentTree.proposals_all if self.args.last_argCommentTree is not None else None,

                 ),
                (self.args.argCommentTree.argTree if self.args.argCommentTree is not None else None,
                 self.args.last_argCommentTree.argTree if self.args.last_argCommentTree is not None else None,

                 ),
                (self.args.argCommentTree.argSearchTree if self.args.argCommentTree is not None else None,
                 self.args.last_argCommentTree.argSearchTree if self.args.last_argCommentTree is not None else None,

                 ),
                (self.args.argCommentTree.arguments_all if self.args.argCommentTree is not None else None,
                 self.args.last_argCommentTree.arguments_all if self.args.last_argCommentTree is not None else None,

                 ),
            ])
            if self.args.argCommentTree is not None:
                self.args.argCommentTree.proposals_all = None
                if self.args.argCommentTree.argTree is not None:
                    self.args.argCommentTree.argTree.clear()
                self.args.argCommentTree.argTree = None
                self.args.argCommentTree.argSearchTree = None
                self.args.argCommentTree.arguments_all = None
            if self.args.last_argCommentTree is not None:
                self.args.last_argCommentTree.proposals_all = None
                if self.args.last_argCommentTree.argTree is not None:
                    self.args.last_argCommentTree.argTree.clear()
                self.args.last_argCommentTree.argTree = None
                self.args.last_argCommentTree.argSearchTree = None
                self.args.last_argCommentTree.arguments_all = None

    def get_args(self, dfr) -> Argumentos:
        if self.from_files:

            try:
                self.args.argCommentTree.proposals_all, self.args.last_argCommentTree.proposals_all = self.get_last_results(dfr, "ArgTrees")[
                    0]
                self.args.argCommentTree.argTree, self.args.last_argCommentTree.argTree = self.get_last_results(
                    dfr, "ArgTrees")[1]
                self.args.argCommentTree.argSearchTree, self.args.last_argCommentTree.argSearchTree = self.get_last_results(dfr, "ArgTrees")[
                    2]
                self.args.argCommentTree.arguments_all, self.args.last_argCommentTree.proposals_all = self.get_last_results(dfr, "ArgTrees")[
                    3]
                return self.args
            except Exception as e:
                print(e)
                self.args = None
                return None
        else:
            return self.args

    def detallecomentario(self, dfr: DFrequest):
        self._last_temaCatProp = "Comentarios"
        return self._aux_detalleComentarioArgumento(dfr, tipo="C")

    def _aux_detalleComentarioArgumento(self, dfr: DFrequest, tipo: str):
        args = self.get_args(dfr)
        if args is None:
            args = Argumentos(dfr)

        def action(ac: Arguments or ProposalComments):
            self.reset_last_results(dfr)
            p = Proposals.query.get(ac.proposalid)

            if args.last_argCommentTree is None:
                args.performArgSearch(data=p, tipo=tipo, withargs=dfr.withargs)
            if tipo == "A":
                self.save_last_results(dfr, "Propuestas", [
                    p
                ])
                if ac.commentid != -1:
                    c = ProposalComments.query.get(ac.commentid)
                    self._last_comment_id = ac.commentid
                    self.save_last_results(dfr, "Comentarios", [c
                                                                ])
                self.save_last_results(dfr, "Argumentos", [
                    ac])

                return arguments.detalle_argumento(
                    ac,
                    p,
                    c
                    if ac.commentid != -1 else None,
                    args.get_sid_of(ac, type=tipo), dfr.withargs)
            elif tipo == "C":
                self.save_last_results(dfr, 'Propuestas', [
                    Proposals.query.get(ac.proposalid), ])

                self.save_last_results(dfr, 'Comentarios', [ac, ])
                return comments.detalle_comentario(
                    ac,
                    p,
                    args.get_sid_of(ac, type=tipo), dfr.withargs)

        ret = self.action_on_something(
            action, dfr, entity=tipo).get_final_response(dfr, "ok")
        self.set_args(dfr, args)
        return ret

    def detalleargumento(self, dfr: DFrequest):
        return self._aux_detalleComentarioArgumento(dfr, tipo="A")

    def argumentoscomentario(self, dfr: DFrequest):
        return self._aux_comentariosargumentos_comentario(dfr, tipo="A")

    def _aux_comentariosargumentos_comentario(self, dfr: DFrequest, tipo: str):
        if dfr.parameters.get("commby") is None:
            dfr.parameters["commby"] = []
        if 'sobrepropuestasanteriores' in dfr.parameters.get('commby'):
            dfr.parameters['propby'] = 'sobrepropuestasanteriores'
            return self.getcomentarios(dfr) if tipo == "C" else self.argumentos(dfr)

        args = self.get_args(dfr)
        if args is None:
            args = Argumentos(dfr)

        def action_on_bycomm(p: ProposalComments):
            self.reset_last_results(dfr)
            p = ProposalComments.query.get(p.id)
            self.save_last_results(dfr, "Propuestas", [
                Proposals.query.get(p.proposalid), ])
            self._last_comment_id = p.id
            self.save_last_results(dfr, "Comentarios", [
                p, ])
            already_performed = False

            if args.last_argCommentTree is None or args.last_argCommentTree.argSearchTree is None:
                already_performed = True
                ret = args.performArgSearch(
                    data=p, tipo=tipo, withargs=dfr.withargs)

            if 'visualizar' in dfr.parameters:
                result = args.last_argCommentTree.argSearchTree.getCommentNode(p.id, p.proposalid).print_tree(prev_sid="", level=1,
                                                                                                              type=tipo if tipo == "C" else "ALL", order_by=dfr.parameters.get('orden'), notoverridesid=False)

                if len(result) == 1:
                    return [args, dfr.addContexts(DFresponse("Lo siento, no se detectaron {} de este comentario".format("comentarios" if tipo == "C" else "argumentos")), ['Argumentos-followup']).get_final_response(dfr)]

                return args, self._getwhatever(dfr,
                                               temaCatProp="Argumentos" if tipo == "A" else "Comentarios",
                                               initializer=lambda: [
                                                   result, "Argumentos" if tipo == "A" else "Comentarios"],
                                               writer=str,
                                               max_limit=comments.MAX_COMMENTS_PER_QUERY,
                                               with_numbers=False,
                                               dont_over_look=True
                                               )
            elif not already_performed:
                ret = args.performArgSearch(
                    data=p, tipo=tipo, withargs=dfr.withargs)
            return args, ret

        if "sobrecomentariounico" in dfr.parameters.get("commby") and len(dfr.parameters.get("commby")) == 1:
            if self.get_last_results(dfr, "Comentarios") is None:
                return DFresponse("No hay comentarios anteriores a los que referirte").get_final_response(dfr)

            ret = args.performArgSearch(
                ProposalComments.query.get(self.get_last_results(dfr, "Comentarios")[0].id), tipo=tipo, withargs=dfr.withargs
            )
        else:
            try:
                dfr.parameters["commby"].remove("sobrecomentariounico")
                dfr.parameters["commby"] = dfr.parameters["commby"][0]
            except:
                if type(dfr.parameters["commby"]) == list and len(dfr.parameters["commby"]) > 0:
                    dfr.parameters["commby"] = dfr.parameters["commby"][0]

        val = self.action_on_something(action_on_bycomm, dfr, entity="C")
        self.from_files = True
        if type(val) == DFresponse:
            self.set_args(dfr, args)
            return dfr.addContexts(val, ['Argumentos-followup']).get_final_response(dfr, "ok")
        args, ret = val
        self.set_args(dfr, args)
        if type(ret) == str:
            return ret
        return ret.get_final_response(dfr, "ok")

    def comentarioscomentario(self, dfr: DFrequest):

        return self._aux_comentariosargumentos_comentario(dfr, tipo="C")

    def helpintent(self, dfr: DFresponse) -> str:
        """
        Gestiona el intent Helpintent

        Se activa cuando el chatbot no entiende lo que dice el usuario

        Args:
            dfr (DFresponse): Request de entrada

        Returns:
            str: Respuesta para DialogFlow en cadena
        """
        return DFresponse(
            fulfillment_message='\[ERROR] No entendí lo que dijiste, lo siento. Escribe "ayuda" para obtener un pequeño manual de uso de este chatbot'
        ).get_final_response(dfr)

    def logs(self, dfr: DFrequest) -> str:
        """
        Gestiona el intent logs.

        Solo se permite para desarrolladores, se activa de momento
        introduciendo "getLogs" en el chatbot

        Args:
            dfr (DFrequest): Request de entrada

        Returns:
            str: Respuesta para DialogFlow en cadena
        """
        print(logs.get_logs(), file=stderr)
        return self._getwhatever(
            dfr,
            "Logs",
            initializer=get_logs,
            writer=logs.writer,
            max_limit=logs.MAX_LOGS_PER_QUERY,
        )

    def registrarcomentario(self, dfr: DFrequest):
        return DFresponse("Su intención de comentar {} la propuesta P{} ha sido registrada correctamente".format(
            "el comentario C{} de".format(int(dfr.parameters.get(
                "commentedcid"))) if dfr.parameters.get("commentedcid") is not None and dfr.parameters.get("commentedcid") != "" else "directamente",
            int(dfr.parameters.get("commentedpid")))).get_final_response(dfr)

    def votarpropuesta(self, dfr: DFrequest):
        return DFresponse("Su intención de apoyar la propuesta P{} ha sido registrada correctamente".format(int(dfr.parameters["votepid"]))).get_final_response(dfr)

    def registrarpropuesta(self, dfr: DFrequest):
        return DFresponse("Su intención de registrar una nueva propuesta {} ha sido guardada correctamente".format("tras ver la propuesta P" + str(int(dfr.parameters.get("createsimilarid"))) if dfr.parameters.get("createsimilarid") is not None else "")).get_final_response(dfr)

    def volver(self, dfr):
        question = self.last_arguments_comments_user_question
        if question is None:
            return DFresponse("Perdona, no sé a dónde quieres volver").get_final_response(dfr, "ok")
        return DFresponse("Pulsa en el botón para volver a la búsqueda original", botones=[[{
            "text": str(question),
            "callback_data": str(question)
        }]]).get_final_response(dfr, "ok")

    def votarcomentario(self, dfr: DFrequest):
        return DFresponse("Su intención de voto _{}_ para el comentario C{} ha sido registrada corresctamente".format(dfr.parameters["Voto"], int(dfr.parameters["votecid"]))).get_final_response(dfr)
