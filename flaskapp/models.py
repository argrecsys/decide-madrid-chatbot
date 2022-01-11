import sqlalchemy
from flask_sqlalchemy import SQLAlchemy

MAX_STR_SIZE_COMMENTS = 200
MAX_STR_SIZE_ARGS = 200
MAX_STR_SIZE_USERNAME = 12
db = SQLAlchemy()

TRADUCCION = {
    "SUPPORT": ["apoyo", "🟩"],
    "ATTACK": ["ataque", "🟥"],
    "QUALIFIER": ["neutral", "🟨"],
    "SUPPORT/ATTACK": ["neutral", "🟨"],
    "OPPOSITION": ["oposición", "😡"],
    "CONTRAST": ["contraste", "🎭"],
    "GOAL": ["objetivo", "🎯"],
    "REASON": ["razón", "🧐"],
    "SIMILARITY": ["similitud", "👥"],
    "CONDITION": ["condición", "🚦"],
    "COMPARISON": ["comparación", "⚖️"],
    "RESULT": ["resultado", "🔜"],
    "ELABORATION": ["elaboración", "📝"],
    "CLARIFICATION": ["aclaración", "👆"],
    "CONSEQUENCE": ["consecuencia", "👉"],
    "RESTATEMENT": ["reafirmación", "👇"],
    "ALTERNATIVE": ["alternativa", "\[🌞/🌝]"],
    "CONCESSION": ["concesión", "🧞‍♂️"],
    "ADDITION": ["añadido", "➕"],
    "EXEMPLIFICATION": ["ejemplificación", "✍️"],
    "CAUSE": ["causa", "🤔➡️"]

}


class CatCategories(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)

    def __repr__(self) -> str:
        return "Categoría: '{}' (id: {})".format(self.name, self.id)


class CatTopics(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    topic = db.Column(db.String(64), nullable=False)
    category = db.Column(db.String(64), nullable=False)


class GeoLocations(db.Model):
    location = db.Column(db.String(128), primary_key=True, nullable=False)
    street = db.Column(db.String(64), nullable=True, default=None)
    type = db.Column(db.String(32), nullable=True, default=None)
    neighborhood = db.Column(db.Integer, primary_key=True, nullable=False)
    district = db.Column(db.Integer, nullable=True)


class GeoDistricts(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(64), nullable=True, default=None)

    def __repr__(self) -> str:
        return "Distrito '{}' (id: {})".format(self.name, self.id)


class GeoNeighborhoods(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(64), nullable=True, default=None)
    districtid = db.Column(
        db.Integer,
        db.ForeignKey("geo_districts.id", ondelete="SET DEFAULT"),
        nullable=True,
        default=None,
    )

    def __repr__(self) -> str:
        return "Barrio '{}', en distrito {} (id: {})".format(
            self.name, self.districtid, self.id
        )


class GeoPois(db.Model):
    poi = db.Column(db.String(128), primary_key=True, nullable=False)
    neighborhood = db.Column(
        db.Integer,
        db.ForeignKey("geo_neighborhoods.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    district = db.Column(
        db.Integer,
        db.ForeignKey("geo_districts.id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )


class GeoStreets(db.Model):
    street = db.Column(db.String(64), primary_key=True, nullable=False)
    neighborhood = db.Column(db.Integer, primary_key=True, nullable=False)
    district = db.Column(db.Integer, primary_key=True, nullable=False)

    def __repr__(self) -> str:
        return "Vía {}, en distrito '{}' y barrio '{}')".format(
            self.street, self.district, self.neighborhood
        )


class MetricsControversy(db.Model):
    proposalid = db.Column(
        db.Integer,
        db.ForeignKey("proposals.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    name = db.Column(db.String(32), primary_key=True, nullable=False)
    value = db.Column(db.Float, nullable=False, default=None)


class MetricsTopicControversy(db.Model):
    topic = db.Column(
        db.Integer,
        db.ForeignKey("proposal_topics.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    name = db.Column(db.String(32), primary_key=True, nullable=False)
    value = db.Column(db.Float, nullable=False, default=None)


class Proposals(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    url = db.Column(db.String(256), nullable=True, default=None)
    code = db.Column(db.String(32), nullable=True, default=None)
    title = db.Column(db.String(256), nullable=True, default=None)
    userid = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    date = db.Column(db.Date, nullable=True)
    summary = db.Column(db.Text, nullable=True)
    text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(16), nullable=True, default=None)
    numcomments = db.Column(db.Integer, nullable=True)
    numsupports = db.Column(db.Integer, nullable=True)
    isassociation = db.Column(db.SmallInteger, nullable=True)

    def __repr__(self) -> str:
        return '"_{}_" ({})*(pid: {})*\[{}👍]'.format(
            self.title, self.date, self.id, self.numsupports
        )


class ProposalTopics(db.Model):
    id = db.Column(
        db.Integer,
        db.ForeignKey("proposals.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    topic = db.Column(db.String(64), primary_key=True, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    n_weight = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(16), nullable=False)


class ProposalTags(db.Model):
    id = db.Column(
        db.Integer,
        db.ForeignKey("proposals.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    tag = db.Column(db.String(64), primary_key=True, nullable=False)


class ProposalLocations(db.Model):
    id = db.Column(
        db.Integer,
        db.ForeignKey("proposals.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    location = db.Column(db.String(128), primary_key=True, nullable=False)
    tag = db.Column(db.String(128), nullable=True, default=None)
    neighborhood = db.Column(db.String(64), primary_key=True, nullable=False)
    district = db.Column(db.String(64), primary_key=True, nullable=True)


class ProposalComments(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    parentid = db.Column(
        db.Integer,
        db.ForeignKey("proposal_comments.id", ondelete="CASCADE"),
        default=-1,
        nullable=True,
    )
    proposalid = db.Column(
        db.Integer, db.ForeignKey("proposals.id", ondelete="CASCADE"), nullable=True
    )
    page = db.Column(db.Integer, nullable=True)
    userid = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET DEFAULT"),
        nullable=True,
        default=None,
    )
    username = db.Column(db.Date, nullable=True
                         )
    usertype = db.Column(db.String(32), nullable=True, default=None)
    date = db.Column(db.Date, nullable=True)
    time = db.Column(db.Time, nullable=True)
    text = db.Column(db.Text, nullable=True)
    numvotes = db.Column(db.Integer, nullable=True)
    numpositivevotes = db.Column(db.Integer, nullable=True)
    numnegativevotes = db.Column(db.Integer, nullable=True)

    def __repr__(self) -> str:
        name = self.username or ""
        if len(name) >= MAX_STR_SIZE_USERNAME:
            name = name[0:MAX_STR_SIZE_USERNAME-1] + "."
        rep = name.replace('_', '__') + " "*(MAX_STR_SIZE_USERNAME -
                                             len(name)) + "| \"" + str(self.text).replace("_", "__")
        # TODO MEJORAR representacion por palabras
        if len(rep) > MAX_STR_SIZE_COMMENTS:
            return "_{}_...\"".format(rep[0:MAX_STR_SIZE_COMMENTS])
        else:
            return "_{}_\"".format(rep)


class ProposalCategories(db.Model):
    id = db.Column(
        db.Integer,
        db.ForeignKey("proposals.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    category = db.Column(db.String(32), primary_key=True, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    n_weight = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(16), nullable=False)


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.String(128), nullable=True, default=None)

    def __repr__(self) -> str:
        return self.name


class Arguments(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   nullable=False, autoincrement=True)
    aid = db.Column(db.Integer, nullable=False)
    sentid = db.Column(db.Integer, nullable=False)
    proposalid = db.Column(
        db.Integer,
        db.ForeignKey("proposals.id", ondelete="CASCADE"),
        nullable=False,
    )
    commentid = db.Column(db.Integer, nullable=False)
    parentid = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(32), nullable=True)
    subcategory = db.Column(db.String(32), nullable=True)
    linkertext = db.Column(db.String(32), nullable=True)

    mainverb = db.Column(db.String(128))
    relationtype = db.Column(db.String(32), nullable=True)
    linker = db.Column(
        db.Integer, db.ForeignKey("arg_linker.id", ondelete="CASCADE"), nullable=True
    )
    premise = db.Column(
        db.Integer, db.ForeignKey("arg_claim.id", ondelete="CASCADE"), nullable=True
    )
    premisetext = db.Column(db.Text, nullable=True)

    sentence = db.Column(db.Text, nullable=False)
    majorclaim = db.Column(
        db.Integer, db.ForeignKey("arg_claim.id", ondelete="CASCADE"), nullable=True
    )
    majorclaimtext = db.Column(db.Text, nullable=True)
    claim = db.Column(
        db.Integer, db.ForeignKey("arg_claim.id", ondelete="CASCADE"), nullable=True
    )
    claimtext = db.Column(db.Text, nullable=True)
    approach = db.Column(db.String(128), nullable=True)
    treelevel = db.Column(db.Integer, nullable=False)
    topic = db.Column(db.String(48), nullable=True)
    aspect = db.Column(db.String(48), nullable=True)

    def escribir_sentence(self):
        val = "\"" + str(self.sentence).replace(
            self.premisetext.replace(' ,', ','), ("*" + (self.premisetext.replace(
                "_", "").replace(
                    "*", "")) + "*")).replace(
                        self.claimtext.replace(' ,', ','), "_" + (self.claimtext.replace(
                            "*", "").replace("_", "")) + "_") + "\""

        return val

    def traducir_to_emoji(exp):
        return TRADUCCION.get(exp.upper())[1] if TRADUCCION.get(exp.upper()) is not None else exp

    def traducir(exp):
        return TRADUCCION.get(exp.upper())[0] if TRADUCCION.get(exp.upper()) is not None else exp

    def traducir_inverso(exp):
        for key, val in TRADUCCION.items():
            if val[0] == exp:
                return key

    def __repr__(self) -> str:
        returned_str =  "Argumento *({}{})*".format(
            "del comentario " if self.commentid != -1 else "de la propuesta ",
            self.commentid
            if self.commentid != -1
            else self.proposalid
        ) + Arguments.traducir_to_emoji(
            self.relationtype.lower()
        ) + Arguments.traducir_to_emoji(
            self.category.upper()
        ) + Arguments.traducir_to_emoji(
            self.subcategory.upper()
        ) + "\n_" + self.sentence[
            0:MAX_STR_SIZE_ARGS
        ].replace('_', '').replace('*', '') + "_"
        if len(self.sentence) > MAX_STR_SIZE_ARGS:
            returned_str = returned_str + "..."
        return returned_str

    def __str__(self) -> str:

        link: ArgLinker = ArgLinker.query.filter(
            ArgLinker.id == self.linker).one()

        return 'Argumento para frase {} de la propuesta {} ("{}"), de tipo [{}] ({} - {}).\n majorclaim: "{}"\nClaim: "{}"\nPremisa: "{}"'.format(
            self.sentid,
            self.proposalid,
            self.sentence,
            link.relationtype,
            link.category,
            link.subcategory,
            self.majorclaimtext,
            self.claimtext,
            self.premisetext,
        )


class ArgCategories(db.Model):
    name = db.Column(db.String(32), primary_key=True, nullable=False)

    def __repr__(self) -> str:
        return self.name


class ArgLinker(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    linker = db.Column(db.Text, nullable=False)
    relationtype = db.Column(db.String(32), nullable=False)
    category = db.Column(
        db.String(32),
        db.ForeignKey("ArgCategories.name", ondelete="CASCADE"),
        nullable=False,
    )
    subcategory = db.Column(
        db.String(32),
        db.ForeignKey("ArgSubCategories.name", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return self.name


class ArgClaim(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    claimtext = db.Column(db.Text, default="")
    type = db.Column(db.String(32))

    def __repr__(self) -> str:
        return (
            str(self.type)
            + " "
            + str(self.id)
            + ", with text: "
            + '"'
            + str(self.claimtext or "")
            + '"'
        )


class ArgEntities(db.Model):
    claimid = db.Column(
        db.Integer,
        db.ForeignKey("ArgCategories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    entity = db.Column(db.Text, primary_key=True, nullable=False)


class ArgNouns(db.Model):
    claimid = db.Column(
        db.Integer,
        db.ForeignKey("ArgCategories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    noun = db.Column(db.Text, primary_key=True, nullable=False)


class ArgSubcategories(db.Model):
    name = db.Column(db.String(32), primary_key=True, nullable=False)

    category = db.Column(
        db.String(32),
        db.ForeignKey("ArgCategories.id", ondelete="CASCADE"),
        nullable=False,
    )

    def __repr__(self) -> str:
        return self.name


class Activities(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   nullable=False, autoincrement=True)
    activity = db.Column(db.Text)

    def __repr__(self) -> str:
        return str(self.activity)


class LogsToActivities(db.Model):
    idlog = db.Column(
        db.Integer,
        db.ForeignKey("logs.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    idactivity = db.Column(
        db.Integer,
        db.ForeignKey("activities.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )


class WithargsSeed(db.Model):
    seed = db.Column(db.Boolean, primary_key=True)


class ChatidToWithargs(db.Model):
    chatid = db.Column(db.BigInteger(), primary_key=True, nullable=False)
    withargs = db.Column(db.Boolean, primary_key=False)


class Logs(db.Model):
    id = db.Column(db.Integer, primary_key=True,
                   nullable=False, autoincrement=True)
    withargs = db.Column(db.Boolean, primary_key=True)
    chatid = db.Column(db.BigInteger(), primary_key=True, nullable=True)
    intent = db.Column(db.Text)
    ts = db.Column(sqlalchemy.TIMESTAMP)
    input = db.Column(db.Text)
    obs = db.Column(db.Text)
    response = db.Column(db.Text, default=None)

    def __repr__(self) -> str:
        return '\[{}- (id: {})] Acts: {} | Input: "{}" | Resp: "{}"'.format(
            str(self.ts),
            self.id,
            str(
                list(
                    Activities.query.with_entities(Activities).join(
                        LogsToActivities,
                        LogsToActivities.idactivity == Activities.id
                        and LogsToActivities.idlog == self.id
                    ).filter(LogsToActivities.idlog == self.id).limit(5).all()
                )
            ),
            self.input,
            self.response,
        )
