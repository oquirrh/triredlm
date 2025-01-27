import json

class NodeStateMachine:
    def __init__(self, node_id):
        self.state = {}
        self.node_id = node_id

    def apply(self, command):
        # Assuming command is a dictionary
        try:
            command = json.loads(command.decode("utf-8"))
            if command["type"] == "set":
                for key, value in command["data"].items():
                    self.state[key] = value
                return json.dumps({"response": "OK", "node": self.node_id})
            elif command["type"] == "get":
                key = command["key"]
                if key in self.state:
                    return json.dumps({"response": self.state[key], "node": self.node_id})
                else:
                    return json.dumps({"response": "Key not found", "node": self.node_id})
            else:
                return json.dumps({"response": "Invalid command type", "node": self.node_id})
        except Exception as e:
            return json.dumps({"response": f"Error: {e}", "node": self.node_id})