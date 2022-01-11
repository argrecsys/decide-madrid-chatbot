
from typing import Dict

from pydialogflow_fulfillment.response import OutputContexts
from flaskapp.models import ChatidToWithargs, db

from flaskapp.utils.df_response import DFresponse


"""
Lista de "criterios" de búsqueda de propuestas esperados. 
Esto son nombres de parámetros leídos de DialogFlow que serán interpretados aquí
Se guarda la lista para saber quçe criterios hay que preguntar al usuario o comprobar
que podemos procesar uno recibido del mismo.
"""

expectedcriterios = [
    "categorias",
    "temas",
    "distritos",
    "barrios",
    # "localizaciones",
    # "texto",
    # "titulo",
    # "fromfecha",
    # "tofecha"
]

ALL_ACTIVITIES = [
    "temas",
    "categorias",
    "sobrepropuestaunica",
    "sobrecomentariounico",
    "barrios",
    "localizaciones",
    "fromfecha",
    "tofecha",
    "argspropuesta",
    "argsportemas",
    "argsafavor",
    "argsencontra",
    "argsconcategorias",
    "argscontemas",
    "argsconentidades",
    "argsconaspectos",
    "argsconargcategory",
    "argsconposicionamiento",
    "argsporcategorias",
    "argsportemas",
    "argsporentidades",
    "argsporaspectos",
    "argsporargcategory",
    "argsporposicionamiento",
    "consid",
    "conid",
    "conindex"

]


class DFrequest:
    parameters: Dict = dict()
    outputContexts = list()
    is_valid_request = False
    intent = str()
    confidence = 1.0
    text = str()
    source = str()
    is_telegram = False
    chat_id = None
    full_json = None
    integration_data = None

    def __init__(self, req):
        self.full_json = req.json
        if "originalDetectIntentRequest" in self.full_json.keys():
            self.is_valid_request = True
        else:
            return

        self.source = req.json["originalDetectIntentRequest"]["source"]
        self.sessionId = req.json["session"].split("/")[-1]
        print("SESSION: " + self.sessionId)
        if self.source == "telegram":
            self.is_telegram = True
            self.integration_data = self.full_json["originalDetectIntentRequest"][
                "payload"
            ]["data"]
            if 'callback_query' in self.integration_data:
                self.integration_data = self.integration_data["callback_query"]
                self.chat_id: str = str(
                    self.integration_data["message"]["chat"]["id"])
            else:
                self.chat_id: str = str(self.integration_data["chat"]["id"])

        self.withargs = True
        """with open(DFrequest.CHATIDS_TO_WITHARGS, "r") as f:
            try:
                self.withargs = json.load(f)[self.chat_id]
            except:
                self.withargs = False"""

        if self.chat_id is not None:
            """if len(self.chat_id) >= 10 and self.chat_id[0] > 2:
                self.chat_id = "1" + self.chat_id[1:10] """
            chat_dude: ChatidToWithargs = ChatidToWithargs.query.get(
                int(self.chat_id))
            if chat_dude is None:
                oldseed_val = db.session.execute(
                    "SELECT seed FROM withargs_seed;").fetchall()[0][0]
                print("OLD SEED:")
                print(oldseed_val)
                oldseed_val = not oldseed_val
                print("NEW SEED:")
                print(oldseed_val)

                db.session.execute("UPDATE withargs_seed SET seed={};".format(
                    "true" if oldseed_val else "false"))
                db.session.commit()
                chat_dude = ChatidToWithargs(
                    chatid=self.chat_id, withargs=oldseed_val)
                db.session.add(chat_dude)
                db.session.commit()

            self.withargs = chat_dude.withargs
        else:
            self.withargs = True
        if self.source != "telegram":
            self.withargs = True
        if "queryResult" in self.full_json:
            self.text = self.full_json["queryResult"]["queryText"]
            self.parameters = self.full_json["queryResult"]["parameters"]
            self.intent = self.full_json["queryResult"]["intent"]["displayName"]
            self.confidence = self.full_json["queryResult"]["intentDetectionConfidence"]
            self.outputContexts = self.full_json["queryResult"]["outputContexts"]
            self.outputContextsNames = list(map(
                lambda ctx: ctx["name"].split("/")[-1], self.outputContexts
            ))

    def get_allactivities(self):
        lista = set()
        lista.add(self.intent)
        allparams: dict = self._get_all_parameters_parsed()
        for k, v in allparams.items():
            if k in ALL_ACTIVITIES:
                lista.add(str(k))
            elif v in ALL_ACTIVITIES:
                lista.add(str(v))
        return lista

    def get_allparameters(self, forproposals=False):
        allparams = self._get_all_parameters_parsed()

        if forproposals:
            for k in set(allparams.keys()):
                if k != "Filtros" and k not in expectedcriterios and k != "orden":

                    try:
                        allparams.pop(k)
                    except KeyError as k:
                        pass

        print("REQ: ALLPARAMS:" + str(allparams))
        return allparams

    def _get_all_parameters_parsed(self):
        allparams = dict(
            filter(
                lambda x: (x[1] != "" and len(x[1]) != 0),
                filter(
                    lambda x: type(x[1]) == list or type(
                        x[1]) == str, self._get_all_parameters_all().items()
                ),
            )
        )
        for k, v in dict(allparams).items():
            if k.endswith(".original"):
                realname = k.replace(".original", "")
                if allparams.get(realname) != None:
                    allparams.pop(k)
                else:
                    allparams.update({realname: v})
                    if type(v) == str:
                        allparams[realname] = str(v).replace(
                            "'", '').replace('"', '')
        return allparams

    def _get_all_parameters_all(self):
        allparams = self.parameters.copy()

        for context in self.outputContexts:
            if "parameters" in context:
                allparams.update(context["parameters"])

        return allparams

    def setparameter(self, parname: str, val: str):
        self.parameters.update({parname: val})

    def addContexts(self, dr: DFresponse, contexts: list):
        for c in contexts:
            dr.add(
                OutputContexts(
                    "chatbot-gubernamental",
                    self.sessionId,
                    c,
                    1,
                    self._get_all_parameters_all(),
                )
            )
        return dr

    def removeContexts(self, dr: DFresponse):
        dr.output_contexts = []
        return dr
