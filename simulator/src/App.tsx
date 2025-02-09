import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { AlertCircle, Power, Send, SunMoonIcon } from 'lucide-react';

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

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };


  return (
    <div className={isDarkMode ? 'dark' : 'light'}>
      <div className="p-4 max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">RAG System Control Panel</h1>
        
        <div className="grid grid-cols-3 gap-4 mb-4">
          {nodes.map(node => (
            <Card key={node.id}>
              <CardHeader>
                <CardTitle className="flex justify-between items-center">
                  <span>Node {node.id}</span>
               
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm">
                  <p>Port: {node.port}</p>
                  <p>Status: {node.status}</p>
                  {node.isLeader && (
                    <p className="text-green-500 font-bold">Leader Node</p>
                  )}
                  {node.status !== 'running' && (
                    <div className="flex items-center text-red-500 mt-2">
                      <AlertCircle className="w-4 h-4 mr-1" />
                      Node is offline
                    </div>
                  )}
                </div>
                <Button
                    variant={node.status === 'running' ? 'default' : 'destructive'}
                    size="sm"
                    onClick={() => toggleNode(node.id)}
                  >
                    <Power className="w-2 h-4 mr-1" />
                    {node.status === 'running' ? 'Running' : 'Stopped'}
                  </Button>
              </CardContent>
            </Card>
          ))}
        </div>
        
        <div className="flex gap-4 mt-8">
          <Input
            type="text"
            placeholder="Enter your query..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1"
          />
          
          <Button onClick={sendQuery} disabled={loading}>
            <Send className="w-4 h-4 mr-2" />
            {loading ? 'Sending...' : 'Send Query'}
          </Button>
        </div>
        
        {response && (
          <Card className="mt-4">
            <CardHeader>
              <CardTitle>Response</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap">{response}</p>
            </CardContent>
          </Card>
        )}
        
        <Button onClick={toggleTheme} className="mt-4">
          <SunMoonIcon></SunMoonIcon>
        </Button>
      </div>
    </div>
  );
};

export default App;