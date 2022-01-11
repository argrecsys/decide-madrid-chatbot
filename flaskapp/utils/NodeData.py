from sqlalchemy.engine.row import LegacyRow
from flaskapp.models import Arguments, ProposalComments, Proposals
from flaskapp.utils.df_utils import ARGS_TO_ENTITIES


class NodeData(object):

    def __init__(self, data: LegacyRow, tipo: str = "?"):

        self.tipo = tipo

        if tipo == "LEGACY_ROW":
            self.tipo = "C"
            self.id = data.proposal_comments_id
            self.proposalid = data.proposal_comments_proposalid
            self.parentid = data.proposal_comments_parentid
            self.commentid = None
            self.numvotes = data.proposal_comments_numvotes
            self.numnegativevotes = data.proposal_comments_numnegativevotes
            self.numpositivevotes = data.proposal_comments_numpositivevotes
            self.date = data.proposal_comments_date
            self.text = data.proposal_comments_text
            self.username = data.proposal_comments_username
            self.userid = data.proposal_comments_userid
            self.time = data.proposal_comments_time

        if tipo == "?":
            try:
                tipo = "A" if data.__getattribute__(
                    'commentid') is not None else "C"
            except:
                try:
                    tipo = "C" if data.__getattribute__(
                        'parentid') is not None else "P"
                except:
                    tipo = "P"

        if tipo != "LEGACY_ROW":
            self.tipo = tipo
            self.id = data.id

        if tipo == "P":
            self.url = data.url
            self.title = data.title
            self.summary = data.summary
            self.code = data.code
            self.date = data.date
            self.isassociation = data.isassociation
            self.numcomments = data.numcomments
            self.numsupports = data.numsupports
            self.status = data.status
            self.text = data.text

        if tipo == "C":
            self.proposalid = data.__getattribute__('proposalid') or -1
            self.parentid = data.__getattribute__('parentid') or -1
            self.numvotes = data.numvotes
            self.numnegativevotes = data.numnegativevotes
            self.numpositivevotes = data.numpositivevotes
            self.date = data.date
            self.text = data.text
            self.username = data.username
            self.userid = data.userid
            self.time = data.time

        if tipo == "A":
            self.proposalid = data.__getattribute__('proposalid') or -1
            self.parentid = data.__getattribute__('parentid') or -1
            self.commentid = data.__getattribute__('commentid') or -1
            self.aid = data.aid
            self.sentid = data.sentid
            self.category = data.category
            self.subcategory = data.subcategory
            self.linkertext = data.linkertext
            self.mainverb = data.mainverb
            self.relationtype = data.relationtype
            self.linker = data.linker
            self.premise = data.premise
            self.premisetext = data.premisetext
            self.sentence = data.sentence
            self.majorclaim = data.majorclaim
            self.majorclaimtext = data.majorclaimtext
            self.claimtext = data.claimtext
            self.approach = data.approach
            self.treelevel = data.treelevel
            self.topic = data.topic
            self.approach = data.approach
            self.entities = ARGS_TO_ENTITIES[self.id]
            self.aspect = data.__getattribute__('aspect') or None

    def __str__(self) -> str:
        if self.tipo == "A":
            val = Arguments.__str__(self)
        elif self.tipo == "C":
            val = ProposalComments.__str__(self)
        elif self.tipo == "P":
            val = Proposals.__str__(self)
        return val

    def __repr__(self) -> str:
        if self.tipo == "A":
            val = Arguments.__repr__(self)
        elif self.tipo == "C":
            val = ProposalComments.__repr__(self)
        elif self.tipo == "P":
            val = Proposals.__repr__(self)
        return val
