import grpc
from raft import service_pb2
from raft.service_pb2_grpc import RaftServicer, RaftStub, add_RaftServicer_to_server
import random
import time
from concurrent import futures
from threading import Lock, Thread, Condition
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RaftNode(RaftServicer):
    def __init__(self, node_id, peers):
        self.node_id = node_id
        self.peers = peers
        self.current_term = 0
        self.voted_for = None
        self.state = "follower"
        self.votes_received = 0
        self.lock = Lock()
        self.leader_id = None
        self.election_timeout_base = 3000
        self.election_timeout_range = 4000
        self.heartbeat_interval = 50
        self.running = True  # New flag for clean shutdown
        self.reset_election_timer()
        self.messages = []
        self.message_condition = Condition()

    def reset_election_timer(self):
        """Reset election timer without requiring lock"""
        self.election_deadline = time.time() + (
            self.election_timeout_base + random.randint(0, self.election_timeout_range)
        ) / 1000.0

    def get_current_state(self):
        """Safe getter for state"""
        with self.lock:
            return self.state

    def get_current_term(self):
        """Safe getter for term"""
        with self.lock:
            return self.current_term

    def start_election(self):
        logger.info(f"Node {self.node_id} starting election")

        # Acquire lock only for state update
        with self.lock:
            if self.state == "leader":
                return

            self.state = "candidate"
            self.current_term += 1
            self.voted_for = self.node_id
            self.votes_received = 1
            current_term = self.current_term  # Store for use outside lock

        self.reset_election_timer()

        # Launch vote requests without holding the lock
        for peer in self.peers:
            Thread(target=self.request_vote_from_peer,
                   args=(peer, current_term),
                   daemon=True).start()

    def request_vote_from_peer(self, peer, term):
        try:
            with grpc.insecure_channel(peer) as channel:
                stub = RaftStub(channel)
                request = service_pb2.RequestVoteArgs(
                    term=term,
                    candidateId=self.node_id,
                    lastLogIndex=0,
                    lastLogTerm=0
                )

                response = stub.RequestVote(
                    request,
                    timeout=self.election_timeout_base
                )

                self.handle_vote_response(response, term)

        except grpc.RpcError as e:
            logger.error(f"Node {self.node_id} error contacting peer {peer}: {e.code()}")
        except Exception as e:
            logger.exception(f"Node {self.node_id} unexpected error contacting peer {peer}")

    def handle_vote_response(self, response, request_term):
        """Handle vote response with minimal lock holding"""
        with self.lock:
            # Verify we're still in the same term and still a candidate
            if self.state != "candidate" or self.current_term != request_term:
                return

            if response.term > self.current_term:
                self.become_follower(response.term)
                return

            if response.voteGranted:
                self.votes_received += 1
                if self.votes_received > len(self.peers) // 2:
                    self.become_leader()

    def become_leader(self):
        """Transition to leader state with minimal lock holding"""
        with self.lock:
            if self.state != "candidate":
                return
            self.state = "leader"
            self.leader_id = self.node_id
            current_term = self.current_term

        logger.info(f"Node {self.node_id} is now the LEADER for term {current_term}")
        Thread(target=self.send_heartbeats, daemon=True).start()

    def become_follower(self, new_term):
        """Transition to follower state with minimal lock holding"""
        with self.lock:
            self.state = "follower"
            self.current_term = new_term
            self.voted_for = None
            self.votes_received = 0

        self.reset_election_timer()

    def RequestVote(self, request, context):
        with self.lock:
            response = service_pb2.RequestVoteReply(
                term=self.current_term,
                voteGranted=False
            )

            if request.term < self.current_term:
                return response

            if request.term > self.current_term:
                self.become_follower(request.term)

            if self.voted_for is None or self.voted_for == request.candidateId:
                self.voted_for = request.candidateId
                response.voteGranted = True
                self.reset_election_timer()

            response.term = self.current_term
            return response

    def AppendEntries(self, request, context):
        with self.lock:
            response = service_pb2.AppendEntriesReply(
                term=self.current_term,
                success=False
            )

            if request.term < self.current_term:
                return response

            if request.term > self.current_term:
                self.become_follower(request.term)

            self.leader_id = request.leaderId
            self.reset_election_timer()
            response.success = True
            response.term = self.current_term
            return response

    def send_heartbeats(self):
        """Send heartbeats without holding the lock"""
        while self.running:  # Check running flag
            current_state = self.get_current_state()
            if current_state != "leader":
                break

            current_term = self.get_current_term()

            # Launch heartbeats without holding the lock
            for peer in self.peers:
                Thread(target=self.send_append_entries,
                       args=(peer, current_term),
                       daemon=True).start()

            time.sleep(self.heartbeat_interval / 1000.0)

    def send_append_entries(self, peer, term):
        """Send AppendEntries with minimal lock holding"""
        try:
            with grpc.insecure_channel(peer) as channel:
                stub = RaftStub(channel)
                request = service_pb2.AppendEntriesArgs(
                    term=term,
                    leaderId=self.node_id,
                    prevLogIndex=0,
                    prevLogTerm=0,
                    entries=[],
                    leaderCommit=0
                )

                response = stub.AppendEntries(
                    request,
                    timeout=self.heartbeat_interval * 2 / 1000.0
                )

                # Handle response with minimal lock holding
                with self.lock:
                    if response.term > self.current_term:
                        self.become_follower(response.term)

        except grpc.RpcError as e:
            logger.error(f"Node {self.node_id} heartbeat error to {peer}: {e.code()}")
        except Exception as e:
            logger.exception(f"Node {self.node_id} unexpected error sending heartbeat to {peer}")

    def election_timer(self):
        """Election timer with minimal lock holding"""
        while self.running:  # Check running flag
            time.sleep(0.1)

            should_start_election = False
            with self.lock:
                if (self.state != "leader" and
                    time.time() > self.election_deadline):
                    should_start_election = True

            if should_start_election:
                self.start_election()

    def shutdown(self):
        """Clean shutdown method"""
        self.running = False

def start_server(node_id, port, peers, raft_node):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_RaftServicer_to_server(raft_node, server)
    server.add_insecure_port(f"0.0.0.0:{port}")

    Thread(target=raft_node.election_timer, daemon=False).start()
    logger.info(f"Node {node_id} started on port {port} with peers {peers}")

    def server_thread():
        server.start()
        server.wait_for_termination()

    Thread(target=server_thread, daemon=True).start()
    return
