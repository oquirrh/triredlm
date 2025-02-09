import grpc
import service_pb2
import service_pb2_grpc


def request_vote(stub, term, candidateId, lastLogIndex, lastLogTerm):
    request = service_pb2.RequestVoteArgs(
        term=term, candidateId=candidateId, lastLogIndex=lastLogIndex, lastLogTerm=lastLogTerm
    )
    response = stub.RequestVote(request)
    print(f"Vote Response: term={response.term}, voteGranted={response.voteGranted}")


def append_entries(stub, term, leaderId, prevLogIndex, prevLogTerm, leaderCommit):
    request = service_pb2.AppendEntriesArgs(
        term=term, leaderId=leaderId, prevLogIndex=prevLogIndex, prevLogTerm=prevLogTerm, leaderCommit=leaderCommit
    )
    response = stub.AppendEntries(request)
    print(f"Append Entries Response: term={response.term}, success={response.success}")


def run():
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = service_pb2_grpc.RaftStub(channel)

        # Send a vote request
        request_vote(stub, term=1, candidateId=1, lastLogIndex=0, lastLogTerm=0)

        # Send an append entries request
        append_entries(stub, term=1, leaderId=1, prevLogIndex=0, prevLogTerm=0, leaderCommit=0)


if __name__ == "__main__":
    run()
