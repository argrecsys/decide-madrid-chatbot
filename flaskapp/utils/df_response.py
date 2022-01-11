
from datetime import datetime
from flaskapp.utils.logs import MAX_STR_SIZE_LOGS, write_log
from pydialogflow_fulfillment.dialogflow_response import DialogflowResponse
from pydialogflow_fulfillment.telegram_response import TelegramMessageResponse, TelegramKeyboardButtonResponse


class DFresponse(DialogflowResponse):

    def __init__(self, fulfillment_message: str = "", webhook_source="webhook", extra_opciones="", parse="markdown", botones: list = None):
        self.parse = parse
        self.extra_opciones = extra_opciones
        self.botones = botones or [[]]
        fulfillment_message = fulfillment_message
        super().__init__(fulfillment_message=fulfillment_message, webhook_source="webhook")
        self.message = fulfillment_message
        if len(self.extra_opciones) > 0:
            self.message = self.message + \
                "\n\nAdemás de usar los botones, ahora puedes escribir frases como éstas:\n" + \
                self.extra_opciones

    def get_final_response(self, dfr, observaciones=None):
        if dfr.is_telegram:
            esto = TelegramMessageResponse(
                self.message, parse_mode=self.parse if dfr.intent != "logs" else "")

            self.add(esto)
            if "\"ayuda\"" in self.message.lower():
                self.botones.insert(0, [{
                    "text": "Ayuda",
                    "callback_data": "ayuda"
                }])
            elif dfr.intent != "GetMore" and (
                dfr.intent != "Filtros" and dfr.intent != "RespuestaFiltro"
                ) and dfr.intent != "ComprobarValor" and (
                    dfr.intent != "SalirGetMore" and dfr.intent != "Saludo"
                    ) and dfr.intent != "bighelp" and dfr.intent != "volver" and (
                        "registrar" not in dfr.intent.lower() and "votar" not in dfr.intent.lower()
                        ) and "ERROR" not in self.message:

                self.botones.insert(0, [{
                    "text": "Preguntar de nuevo",
                    "callback_data": str(dfr.text)
                }, ])
            if dfr.intent.lower() == "detallecomentarios" or dfr.intent.lower() == "detalleargumentos":
                self.botones.insert(0, [{
                    "text": "Volver a pregunta inicial",
                    "callback_data": "volver"
                }, ])
            if len(self.botones[0]) == 0:
                index = 0
            else:
                index = 1
            if (dfr.intent == "GetPropuestas" or dfr.intent == "Filtros" or dfr.intent == "RespuestaFiltro" or dfr.intent == "ComprobarValor") and "?" in self.message:

                self.botones[index].append({
                    "text": "Sí",
                    "callback_data": "Si"
                })
                if dfr.intent != "GetPropuestas":
                    try:
                        self.botones[index+1].append({
                            "text": "Ejecutar",
                            "callback_data": "Ejecutar"
                        })
                    except:
                        self.botones.append([{
                            "text": "Ejecutar",
                            "callback_data": "Ejecutar"
                        }])
                self.botones[index].append({
                    "text": "No",
                    "callback_data": "No"
                })
                self.botones[index].append({
                    "text": "Cancelar petición",
                    "callback_data": "Cancelar"
                })
            elif (dfr.intent == "ComprobarValor"):
                self.botones[index].append({
                    "text": "Salir",
                    "callback_data": "Salir"
                })

            print("BOTONES")
            print(self.botones)
            if len(self.botones) > 0 and len(self.botones[0]) > 0:
                self.add(TelegramKeyboardButtonResponse(
                    "Puedes pulsar los siguientes botones" if "help" not in str(dfr.intent).lower() else "*TEMAS DE AYUDA*:", self.botones))
            if dfr.intent != "logs":
                write_log(chatid=dfr.chat_id, withargs=dfr.withargs, intent=dfr.intent, activity=dfr.get_allactivities(), ts=datetime.now(
                ), observaciones="error" if "[ERROR]" in self.message else observaciones or "ok", input=dfr.text, response=self.message[0:MAX_STR_SIZE_LOGS])
        print("PARAMS: " + str(dfr.parameters))
        print("CHATID: " + str(dfr.chat_id))
        print("WITHARGS: " + str(dfr.withargs))
        print("MESSAGE: " + self.message)
        if "[ERROR]" in self.message:
            self = dfr.removeContexts(self)
        return super().get_final_response()
