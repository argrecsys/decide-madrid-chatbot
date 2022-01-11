from flaskapp.models import ProposalComments, Proposals, Users
from flaskapp.utils.df_response import DFresponse

MAX_COMMENTS_PER_QUERY = 4
MAX_COMMENT_STATS_PER_QUERY = 3


def detalle_comentario(c: ProposalComments, p: Proposals, sid: str = None, withargs=True):
    res = "El comentario indicado tiene estas características:\n"
    text = c.text
    url = p.url
    username = Users.query.get(c.userid).name.replace("_", "__")
    isassoc = p.isassociation
    res = "*C{}* - Comentario de la propuesta {}{} por \"_{}_\"{}\nURL de propuesta: {}\n\n_{}_\n\n{}\n".format(
        c.id,
        p.id,
        ", en contestación al comentario '_raíz_' C{}".format(
            c.parentid) if c.parentid != -1 else "",
        username, "(assoc.)" if isassoc else "",
        "https://decide.madrid.es/"+url,
        text.replace("_", "\_"),
        "**El comentario tiene {} votos, de los cuales:\n   -{} votos positivos\n   -{} votos negativos\n".format(c.numvotes, c.numpositivevotes, c.numnegativevotes))

    return DFresponse(res, botones=[
        [

            {
                "text": "Ver respuestas",
                "callback_data": "Comentarios del comentario con id {}".format(c.id)
            },
            {
                "text": "Ver propuesta",
                "callback_data": "Ver propuesta con id {}".format(c.proposalid)
            }
        ], [{
            "text": "Ver argumentos",
            "callback_data": "Argumentos sobre el comentario con id {}".format(c.id)
        }] if withargs else [],
        [
            {
                "text": "Ver comentario raíz (C{})".format(c.parentid),
                "callback_data": "Ver comentario con id {}".format(c.parentid)
            }
        ] if c.parentid != -1 else [],
        [
            {
                "text": "RESPONDER AL COMENTARIO",
                "callback_data": "registrar comentario sobre {} de la propuesta {}".format(c.id, p.id)
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
                "text": "VOTAR POSITIVAMENTE",
                "callback_data": "registrar punto positivo a comentario {}".format(c.id)
            },
            {
                "text": "VOTAR NEGATIVAMENTE",
                "callback_data": "registrar punto negativo a comentario {}".format(c.id)
            }
        ]
    ])
