import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { AlertCircle, Power, Send, Sun , Moon } from 'lucide-react';

const App = () => {
  const [nodes, setNodes] = useState([
    { id: 1, port: 50051, status: 'unknown', isLeader: false },
    { id: 2, port: 50052, status: 'unknown', isLeader: false },
    { id: 3, port: 50053, status: 'unknown', isLeader: false }
  ]);
  
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);

  useEffect(() => {
    // Poll node status every 5 seconds
    const interval = setInterval(refreshNodeStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const refreshNodeStatus = async () => {
    const updatedNodes = await Promise.all(
      nodes.map(async node => {
        try {
          const response = await fetch(`http://localhost:${node.port}/status`);
          const data = await response.json();
          return {
            ...node,
            status: data.status,
            isLeader: data.is_leader
          };
        } catch (error) {
          return {
            ...node,
            status: 'error',
            isLeader: false
          };
        }
      })
    );
    setNodes(updatedNodes);
  };

  const toggleNode = async (nodeId: number) => {
    const node = nodes.find(n => n.id === nodeId);
    const action = node.status === 'running' ? 'stop' : 'start';
    
    try {
      await fetch(`http://localhost:${node.port}/${action}`, {
        method: 'POST'
      });
      await refreshNodeStatus();
    } catch (error) {
      console.error(`Failed to ${action} node:`, error);
    }
  };

  const sendQuery = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    try {
      // Find the leader node
      const leaderNode = nodes.find(node => node.isLeader);
      if (!leaderNode) {
        setResponse('No leader node available');
        return;
      }
      
      const response = await fetch(`http://localhost:${leaderNode.port}/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
      });
      
      const data = await response.json();
      setResponse(data.response);
    } catch (error) {
      setResponse('Error: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleTheme = () => setIsDarkMode(!isDarkMode);



  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-900'}`}>
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">TRI RED LM AGENT INFERENCE CONRTOL PANEL</h1>
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={toggleTheme}>
            {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-8">
        <div className="space-y-6">
          {/* System Status Panel */}
          <Card className="bg-slate-800 text-white border-slate-700">
            <CardHeader>
              <CardTitle>SYSTEM STATUS</CardTitle>
            </CardHeader>
           <CardContent>
            <Card className="bg-slate-800 text-white border-slate-700">
              <CardContent className={`overflow-y-auto h-48 text-xs ${isDarkMode ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-900'} `}>
              The advent of LLMs has revolutionized AI-driven decision-making, yet their deployment in mission-critical environments like space systems demands unparalleled reliability.<p> This paper presents a distributed LLM architecture with majority voting, designed for fault tolerance and robustness in resource-constrained settings.</p><p> By leveraging a triple-redundant system of LLM nodes equipped with RAG and synchronized vector databases, the framework ensures consistent outputs even under node failures.</p><p> A de-centralized voting coordinator employs semantic similarity analysis to resolve discrepancies, while Docker-based containerization enables scalable, isolated deployment.</p> The MVP demonstrates the feasibility of this approach using lightweight models and consensus-driven response aggregation, laying the groundwork for resilient AI systems in space and beyond.
              </CardContent>
            </Card>
            <img src="./dragon.png" alt="space-craft" />
           </CardContent>
          </Card>


        </div>

        {/* Command Center */}
        <div className="space-y-6">
                    {/* Node Grid */}
                    <div className="grid grid-cols-3 gap-4">
            {nodes.map(node => (
              <Card key={node.id} className="bg-slate-800 text-white border-slate-700">
                <CardContent className="pt-6">
                  <div className="text-center">
                    <div className={`inline-flex items-center justify-center w-12 h-12 rounded-full mb-4 ${
                      node.status === 'running' ? 'bg-green-500/20' : 'bg-red-500/20'
                    }`}>
                      <Power className={`w-6 h-6 ${
                        node.status === 'running' ? 'text-green-500' : 'text-red-500'
                      }`} />
                    </div>
                    {node.isLeader && (
                    <p className="text-green-500 font-bold">Leader Node</p>
                  )}
                    <h3 className="font-bold mb-2">NODE {node.id}</h3>
                    <p className="text-sm text-slate-400">Port: {node.port}</p>
                    <Button
                      variant={node.status === 'running' ? 'outline' : 'destructive'}
                      size="sm"
                      className="mt-4 text-primary"
                      onClick={() => toggleNode(node.id)}
                    >
                      {node.status === 'running' ? 'ONLINE' : 'OFFLINE'}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
          <Card className="bg-slate-800 text-white border-slate-700">
            <CardHeader>
              <CardTitle>COMMAND CENTER</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <Input
                  type="text"
                  placeholder="Enter command sequence..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="bg-slate-900 border-slate-700 text-white"
                />
                <Button 
                  className="w-full bg-blue-600 hover:bg-blue-700"
                  onClick={sendQuery} 
                  disabled={loading}
                >
                  <Send className="w-4 h-4 mr-2" />
                  {loading ? 'PROCESSING...' : 'EXECUTE COMMAND'}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800 text-white border-slate-700 h-128">
            <CardHeader>
              <CardTitle>SYSTEM OUTPUT</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="font-mono text-sm text-green-400 overflow-y-auto max-h-96">
                {response || '> Awaiting command input...'}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  </div>
  );
};

export default App;