import json
import os
import time
import traceback
import grpc
from concurrent import futures
from threading import Thread

import raftos
from state_machine import NodeStateMachine  # Import the corrected state machine
from rag import RAG
from utils import calculate_similarity, get_other_nodes
import service_pb2
import service_pb2_grpc

class QueryService(service_pb2_grpc.QueryServiceServicer):
    def __init__(self, raft_node):
        self.raft_node = raft_node
        self.rag = RAG()

    def Query(self, request, context):
        print(f"Received query: {request.query}")
        try:
            # Make sure this operation is performed only by the leader
            if self.raft_node.is_leader():
                # Apply the query as a command to the Raft cluster
                command = {
                    "type": "query",
                    "data": {"query": request.query}
                }
                # Serialize the command to a string
                command_str = json.dumps(command)

                # Apply the command via Raft, which will update the state machine
                # Ensure apply_log returns a result that can be processed
                result = self.raft_node.apply_log(command_str, True)
                print(f"Result from Raft: {result}")
                return service_pb2.QueryResponse(response=result)
            else:
                # Optionally, forward the request to the current leader
                leader_address = self.raft_node.get_leader_address()
                if leader_address:
                    print(f"Forwarding query to leader at {leader_address}")
                    with grpc.insecure_channel(leader_address) as channel:
                        stub = service_pb2_grpc.QueryServiceStub(channel)
                        return stub.Query(request)
                else:
                    return service_pb2.QueryResponse(response="Leader not known")
        except Exception as e:
            print(f"Error during Query: {e}")
            traceback.print_exc()
            return service_pb2.QueryResponse(response=f"Error: {e}")

def serve():
    node_id = os.environ.get("RAFT_ID")
    raft_port = int(os.environ.get("RAFT_PORT"))
    other_nodes = get_other_nodes(node_id)

    # Initialize the state machine
    state_machine = NodeStateMachine(node_id)

    # Initialize and start Raft node
    raft_node = raftos.RaftNode(node_id, raft_port, state_machine, other_nodes)
    raftos.configure_logging(node_id, '/app/log')
    raft_thread = Thread(target=raft_node.run_forever)
    raft_thread.daemon = True
    raft_thread.start()

    # Wait for Raft node to be ready
    time.sleep(5)  # Adjust this delay as needed

    # Initialize gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    service_pb2_grpc.add_QueryServiceServicer_to_server(
        QueryService(raft_node), server
    )
    server.add_insecure_port(f"[::]:50051")
    server.start()
    print(f"gRPC server started on port 50051 for {node_id}")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()