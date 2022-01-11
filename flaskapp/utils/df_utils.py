import os
from typing import Any, Callable, Iterable
import unicodedata

import sqlalchemy

from flaskapp.proposals import DEFAULT_CONTROVERSY


def normalize(c):
    return unicodedata.normalize("NFD", c)[0]


def quitar_tildes(data):
    return str(''.join(normalize(c) for c in str(data)))


def get_entities(engine: sqlalchemy.engine.Engine, tipo):
    result = dict()
    arguments = list(engine.execute(
        "SELECT id, claim, majorclaim, premise FROM arguments;").fetchall())
    entities = "SELECT entity as e, COUNT(*) as c FROM arg_entities WHERE claimid={} OR claimid={} OR claimid={} GROUP BY entity ORDER BY c DESC;"
    for a in arguments:
        result[a[0]] = list(engine.execute(
            entities.format(a[1], a[2], a[3])).fetchall())
    return result


def get_controversy(engine: sqlalchemy.engine.Engine):
    result = dict()
    DEFAULT_CONTROVERSY
    metrics = engine.execute("SELECT m.proposalid, m.value FROM metrics_controversy as m WHERE m.name = \'{}\';".format(
        DEFAULT_CONTROVERSY)).fetchall()
    for l in metrics:
        result[l[0]] = l[1]
    return result


ENGINE = sqlalchemy.create_engine(os.environ.get(
    "DATABASE_URL").replace("postgres://", "postgresql://"))
ARGS_TO_ENTITIES = get_entities(tipo="claim", engine=ENGINE)

PROPS_TO_CONTROVERSY = get_controversy(ENGINE)


def list_to_telegram(
    lista: Iterable, writer: Callable[[Any], str] = lambda x: str(x), offset=0, with_numbers=True
) -> str:
    resultados_str = ""
    for index, result in enumerate(lista):
        resultados_str += "- *{})* {}\n".format(index + 1 + offset, writer(
            result)) if with_numbers else "-|-{}\n".format(writer(result))
    return resultados_str
