class RequestVoteArgs:
    def __init__(self):
        self.term = None
        self.candidateId = None
        self.lastLogIndex = None
        self.lastLogTerm = None

    def __init__(self, term, candidateId, lastLogIndex, lastLogTerm):
        self.term = term
        self.candidateId = candidateId
        self.lastLogIndex = lastLogIndex
        self.lastLogTerm = lastLogTerm


class RequestVoteReply:
    def __init__(self, term, voteGranted):
        self.term = term
        self.voteGranted = voteGranted
