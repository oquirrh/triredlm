class AppendEntriesArgs:
    def __init__(self):
        self.term = None
        self.leaderId = None
        self.prevLogIndex = None
        self.prevLogTerm = None
        self.entries = []
        self.leaderCommit = None

    def __int__(self, term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit):
        self.term = term
        self.leaderId = leaderId
        self.prevLogIndex = prevLogIndex
        self.prevLogTerm = prevLogTerm
        self.entries = entries
        self.leaderCommit = leaderCommit


class AppendEntriesReply:
    def __init__(self, term, success):
        self.term = term
        self.success = success