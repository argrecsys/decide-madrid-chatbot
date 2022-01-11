
from flaskapp.models import Proposals, Users
from flaskapp.utils.df_response import DFresponse

DEFAULT_CONTROVERSY = 'OPINION_POLARIZATION'
MAX_TEMAS_PER_QUERY = 20
MAX_PROPOSALS_LIMIT = 500


def detalle_propuesta(p: Proposals, withargs=True):
    res = "La propuesta indicada tiene estas características:\n"
    title = p.title
    text = p.summary
    url = p.url
    username = Users.query.get(p.userid).name
    isassoc = p.isassociation
    if len(text) < 2:
        text = title
    res = "\"{}\" (id: {}) por {}{}\n URL: {}\n\n_{}_\n\n{}\n{}\nPuedes también realizar las acciones de abajo, pulsando el botón correspondiente. (Tan sólo se registrará tu _intención_ de hacer esas acciones si el chatbot funcionara de forma oficial)".format(
        title, p.id, username, "(assoc.)" if isassoc else "",
        "https://decide.madrid.es/"+url,
        str(text).replace("_", "\_"),
        "**La propuesta tiene {} apoyos\n".format(p.numsupports),
        "**La propuesta consta de {} comentarios. Para verlos, pulsa el botón correspondiente o escribe en cualquier momento '_Ver comentarios para la propuesta con pid {}_'".format(
            p.numcomments, p.id) if p.numcomments > 0 else "La propuesta no tiene comentarios aún",

    )

    return DFresponse(res, botones=[
        [
            {
                "text": "Ver comentarios",
                "callback_data": "Comentarios de la propuesta con id {}".format(p.id)
            },
            {
                "text": "Ver argumentos",
                "callback_data": "Argumentos de la propuesta con id {}".format(p.id)
            }
        ] if withargs else [{
            "text": "Ver comentarios",
            "callback_data": "Comentarios de la propuesta con id {}".format(p.id)
        }],
        [] if not withargs else [{
            "text": "Ver comentarios y argumentos",
            "callback_data": "Ver comentarios y argumentos".format(p.id)
        }],
        [
            {
                "text": "DAR MI APOYO",
                "callback_data": "registrar apoyo para {}".format(p.id)
            }
        ],
        [
            {
                "text": "HACER UN COMENTARIO",
                "callback_data": "registrar comentario para propuesta {}".format(p.id)
            }
        ],
        [
            {
                "text": "HACER UNA NUEVA PROPUESTA",
                "callback_data": "registrar propuesta similar a {}".format(p.id)
            }
        ]
    ])
