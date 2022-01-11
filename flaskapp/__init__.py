import os
from sys import stderr

from flask import Flask, abort, request

from flaskapp.intents import BASE_PICKLE_ROUTE, IntentManager
from flaskapp.models import *
from flaskapp.utils.df_request import DFrequest
from flaskapp.utils.df_response import DFresponse



def create_app():
    app = Flask(__name__)

    app.config.from_object(os.environ["APP_SETTINGS"])
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    print(app.config)

    intmanagers = dict()

    os.makedirs(BASE_PICKLE_ROUTE, exist_ok=True)

    
    @app.route("/webhook", methods=["POST", "GET"])
    def webhook():
        """
        Este endpoint gestiona el webhook del chatbot.
        Realiza llamadas a funciones de intents.py para
        gestionar cada posible entrada de cada posible usuario.
        Mantiene un mapa de ids de conversaciones "chat_id" a
        manejadores de intents para esa conversación, objetos
        de la clase "IntentManager".
        """
        if request.method == "POST":

            mensaje = "Algo falla"
            dfr = DFrequest(request)
            print("Request")
            print(str(request.json))
            if dfr.is_valid_request:
                if dfr.intent != "Saludo":
                    intmanager: IntentManager = intmanagers.get(dfr.chat_id)
                    if intmanager is None:
                        intmanagers.update({dfr.chat_id: IntentManager(dfr)})
                        intmanager = intmanagers.get(dfr.chat_id)
                    return intmanager._call_intent(dfr.intent, dfr)
                else:
                    
                    mensaje = """Bienvenido/a, estás hablando con un chatbot de gobierno colaborativo experimental cuyo fin es mejorar el sistema de participación ciudadana "_Decide Madrid_"."""
                    if dfr.source == "DIALOGFLOW_CONSOLE":
                        mensaje += "\nPor cierto, veo que estás hablandome desde DialogFlow, así que debes ser administrador del chatbot. Perdón por la charla"
                    elif dfr.source == "telegram":
                        mensaje += (
                            "\nCon el fin de realizar un estudio académico, guardaremos tu nombre de Telegram ("
                            + (str(dfr.integration_data["from"]["first_name"]) if dfr.integration_data.get('from') is not None and  dfr.integration_data.get('from').get("first_name") is not None else "_Vaya bueno, no tienes nombre! al parecer_")
                            + ") y un token de identificación del chat *(chat**_**id)*: "
                            + "`"
                            + str(dfr.chat_id)
                            + "`"
                            + ".\n"
                            + "La autoría de las actividades que los asistentes "
                            + "al experimento realicen estará únicamente registrada "
                            + "con ese chat\_id, por lo que tus datos personales no serán "
                            + "asociados al experimento. *¡Gracias por tu colaboración!*\n"
                            + "Para ver una mayor explicación de esta herramienta, escribe o pulsa en \"ayuda\". Si tras leer esa ayuda el chatbot no consigue ayudarte, no dudes en contactar con los desarrolladores por Telegram: [t.me/andres_holgsanc](t.me/andres_holgsanc)"
                        )
                    else:
                        mensaje += "\n No sé qué plataforma estás usando para comunicarte conmigo. Debes usar Telegram para que el experimento funcione, por favor. Este es el enlace del bot: [](https://t.me/chat_tfg_coll_bot)"
                    return DFresponse(mensaje).get_final_response(dfr)
        else:
            abort(400)


    @app.route("/")
    def service_check():

        return "Servicio abierto"


    @app.route("/pruebaservicio")
    def get_all():

        a = Users.query.limit(5)
        for e in a:
            print("Usuario:", file=stderr)
            print(e.name, file=stderr)
            print("...", file=stderr)

        return str(list(a))
    return app
