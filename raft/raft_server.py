import grpc
import service_pb2
import service_pb2_grpc
import random
import time
from concurrent import futures
from threading import Lock, Thread

class RaftNode(service_pb2_grpc.RaftServicer):
    def __init__(self, node_id, peers):
        self.node_id = node_id
        self.peers = peers  # List of other Raft nodes
        self.current_term = 0
        self.voted_for = None
        self.state = "follower"  # Can be "follower", "candidate", "leader"
        self.votes_received = 0
        self.lock = Lock()
        self.leader_id = None
        self.election_timeout = random.uniform(3, 5)  # Random timeout in seconds
        self.reset_election_timer()

    def reset_election_timer(self):
        """Restart the election timeout"""
        self.election_deadline = time.time() + self.election_timeout

    def start_election(self):
        """Trigger an election when timeout occurs"""
        with self.lock:
            if self.state == "leader":
                return

            self.state = "candidate"
            self.current_term += 1
            self.voted_for = self.node_id
            self.votes_received = 1  # Vote for self

            print(f"Node {self.node_id} is starting an election for term {self.current_term}")

        # Request votes from other nodes
        threads = []
        for peer in self.peers:
            t = Thread(target=self.request_vote_from_peer, args=(peer,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    def request_vote_from_peer(self, peer):
        """Send a vote request to another peer"""
        try:
            with grpc.insecure_channel(peer) as channel:
                stub = service_pb2_grpc.RaftStub(channel)
                request = service_pb2.RequestVoteArgs(
                    term=self.current_term, candidateId=self.node_id, lastLogIndex=0, lastLogTerm=0
                )
                response = stub.RequestVote(request)

                with self.lock:
                    if response.voteGranted:
                        self.votes_received += 1
                        if self.votes_received > len(self.peers) // 2:
                            self.become_leader()
        except Exception as e:
            print(f"Error contacting peer {peer}: {e}")

    def become_leader(self):
        """Convert to leader if election is won"""
        self.state = "leader"
        self.leader_id = self.node_id
        print(f"Node {self.node_id} is now the LEADER for term {self.current_term}")

    def RequestVote(self, request, context):
        """Handles incoming vote requests"""
        response = service_pb2.RequestVoteReply(term=self.current_term, voteGranted=False)

        with self.lock:
            if request.term > self.current_term:
                self.current_term = request.term
                self.voted_for = None
                self.state = "follower"

            if self.voted_for is None or self.voted_for == request.candidateId:
                self.voted_for = request.candidateId
                response.voteGranted = True
                print(f"Node {self.node_id} voted for {request.candidateId} in term {request.term}")

        response.term = self.current_term
        return response

    def AppendEntries(self, request, context):
        """Handles AppendEntries (heartbeat from leader)"""
        response = service_pb2.AppendEntriesReply(term=self.current_term, success=False)

        with self.lock:
            if request.term < self.current_term:
                return response

            self.current_term = request.term
            self.leader_id = request.leaderId
            self.state = "follower"
            self.reset_election_timer()
            response.success = True

        print(f"Node {self.node_id} received heartbeat from leader {request.leaderId}")
        return response

    def election_timer(self):
        """Runs a loop to check for election timeouts"""
        while True:
            time.sleep(1)
            if self.state != "leader" and time.time() > self.election_deadline:
                self.start_election()
                self.reset_election_timer()

def start_server(node_id, port, peers):
    """Start a Raft node server"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    raft_node = RaftNode(node_id, peers)
    service_pb2_grpc.add_RaftServicer_to_server(raft_node, server)
    server.add_insecure_port(f"[::]:{port}")

    # Start election timer in a separate thread
    Thread(target=raft_node.election_timer, daemon=True).start()

    print(f"Node {node_id} started on port {port} with peers {peers}")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    import sys
    node_id = int(sys.argv[1])  # Node ID from command-line arguments
    port = int(sys.argv[2])  # Port to run the server
    peers = sys.argv[3:]  # List of peer addresses (e.g., ["localhost:50052", "localhost:50053"])

    start_server(node_id, port, peers)
