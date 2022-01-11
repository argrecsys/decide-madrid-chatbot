from typing import Any

from flaskapp.models import Activities, Logs, LogsToActivities, db
from sqlalchemy.sql.expression import desc, func

"""
Este modulo contiene funciones para escribir y leer los logs desde el chatbot
"""
MAX_LOGS_PER_QUERY = 5
MAX_STR_SIZE_LOGS = 128


def write_log(
    chatid: int,
    intent: str,
    activity: set,
    ts: Any,
    input: str,
    response: str,
    observaciones: str,
    id: int = -1,
    withargs: bool = False
):
    if id == -1:
        try:
            idlog = db.session.query(func.max(Logs.id)).scalar() + 1
        except:
            idlog = 1
        db.session.add(
            Logs(
                id=idlog,
                chatid=chatid,
                intent=intent,
                input=input,
                ts=ts,
                response=response,
                obs=observaciones,
                withargs=withargs
            )
        )
    else:
        db.session.add(
            Logs(
                chatid=chatid,
                intent=intent,
                input=input,
                ts=ts,
                response=response,
                obs=observaciones,
                id=id,
                withargs=withargs
            )
        )
    db.session.commit()
    print("ACTITVITIES TO LOG: " + str(activity))
    for act in activity:
        if act == intent:
            continue
        idactivity = None
        try:
            idactivity = Activities.query.filter_by(activity=act).first().id
        except:
            db.session.add(
                Activities(
                    activity=act
                )
            )
            db.session.commit()
            idactivity = db.session.query(func.max(Activities.id)).scalar()

        db.session.add(
            LogsToActivities(idlog=idlog, idactivity=idactivity)
        )
        db.session.commit()


def get_logs(limit=100):
    query = Logs.query.order_by(desc(Logs.ts)).limit(limit)
    return query.all(), query


def writer(x: Logs):
    rep = repr(x)
    if len(rep) > MAX_STR_SIZE_LOGS:
        return "{}...".format(rep[0:MAX_STR_SIZE_LOGS])
    else:
        return rep
