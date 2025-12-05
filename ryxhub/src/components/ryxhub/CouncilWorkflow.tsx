import { useState, useEffect } from 'react';
import { Brain, Users, TrendingUp, TrendingDown, AlertTriangle, Check, X, Loader2, Play, Pause, RotateCcw } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';

interface WorkerModel {
  id: string;
  name: string;
  model: string;
  status: 'active' | 'warning' | 'fired';
  performance: number; // 0-100
  tasksCompleted: number;
  successRate: number;
  avgQuality: number;
  avgLatency: number;
  lastTask?: string;
  logs: string[];
}

interface CouncilTask {
  id: string;
  prompt: string;
  status: 'pending' | 'searching' | 'rating' | 'complete';
  results: {
    workerId: string;
    workerName: string;
    response: string;
    quality: number;
    latency: number;
    sources?: string[];
  }[];
  supervisorDecision?: string;
  timestamp: string;
}

export function CouncilWorkflow() {
  const [workers, setWorkers] = useState<WorkerModel[]>([
    {
      id: 'worker-1',
      name: 'Alpha',
      model: 'qwen2.5-3b',
      status: 'active',
      performance: 85,
      tasksCompleted: 12,
      successRate: 0.92,
      avgQuality: 8.2,
      avgLatency: 850,
      logs: ['Started', 'Completed 12 tasks successfully'],
    },
    {
      id: 'worker-2',
      name: 'Beta',
      model: 'phi-3.5-mini',
      status: 'active',
      performance: 72,
      tasksCompleted: 10,
      successRate: 0.80,
      avgQuality: 7.0,
      avgLatency: 920,
      logs: ['Started', 'Performance improving'],
    },
    {
      id: 'worker-3',
      name: 'Gamma',
      model: 'gemma-2-2b',
      status: 'warning',
      performance: 45,
      tasksCompleted: 8,
      successRate: 0.62,
      avgQuality: 5.5,
      avgLatency: 1100,
      logs: ['Started', 'Inconsistent performance', 'Supervisor attempting refinement'],
    },
  ]);

  const [tasks, setTasks] = useState<CouncilTask[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentTask, setCurrentTask] = useState<string>('');

  const getPerformanceColor = (performance: number) => {
    if (performance >= 70) return 'text-green-500';
    if (performance >= 40) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getPerformanceBg = (performance: number) => {
    if (performance >= 70) return 'bg-green-500/10';
    if (performance >= 40) return 'bg-yellow-500/10';
    return 'bg-red-500/10';
  };

  const getStatusIcon = (status: WorkerModel['status']) => {
    switch (status) {
      case 'active':
        return <Check className="w-4 h-4 text-green-500" />;
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
      case 'fired':
        return <X className="w-4 h-4 text-red-500" />;
    }
  };

  const handleStartTask = async () => {
    if (!currentTask.trim()) {
      toast.error('Please enter a task');
      return;
    }

    const newTask: CouncilTask = {
      id: `task-${Date.now()}`,
      prompt: currentTask,
      status: 'pending',
      results: [],
      timestamp: new Date().toLocaleTimeString(),
    };

    setTasks(prev => [newTask, ...prev]);
    setIsRunning(true);
    setCurrentTask('');

    // Simulate council workflow
    await simulateCouncilTask(newTask);
  };

  const simulateCouncilTask = async (task: CouncilTask) => {
    // Phase 1: Searching
    await new Promise(resolve => setTimeout(resolve, 500));
    updateTask(task.id, { status: 'searching' });

    // Phase 2: Workers respond (simulate)
    const activeWorkers = workers.filter(w => w.status !== 'fired');
    const workerResults = await Promise.all(
      activeWorkers.map(async (worker, idx) => {
        await new Promise(resolve => setTimeout(resolve, 1000 + idx * 300));
        const quality = Math.max(1, Math.min(10, worker.avgQuality + (Math.random() - 0.5) * 2));
        return {
          workerId: worker.id,
          workerName: worker.name,
          response: `Worker ${worker.name} response to: "${task.prompt.substring(0, 50)}..." (Quality: ${quality.toFixed(1)}/10)`,
          quality,
          latency: worker.avgLatency + Math.random() * 200,
          sources: [`Source 1 (${worker.name})`, `Source 2 (${worker.name})`],
        };
      })
    );

    updateTask(task.id, { results: workerResults });
    
    // Phase 3: Rating
    await new Promise(resolve => setTimeout(resolve, 800));
    updateTask(task.id, { status: 'rating' });

    // Update worker performance based on results
    const updatedWorkers = workers.map(worker => {
      const result = workerResults.find(r => r.workerId === worker.id);
      if (!result) return worker;

      const newQuality = (worker.avgQuality * worker.tasksCompleted + result.quality) / (worker.tasksCompleted + 1);
      const newPerformance = Math.round(newQuality * 10);
      
      let newStatus: WorkerModel['status'] = 'active';
      const newLogs = [...worker.logs];

      if (newPerformance < 40 && worker.tasksCompleted + 1 >= 5) {
        newStatus = 'fired';
        newLogs.push(`🔥 FIRED: Performance dropped to ${newPerformance}%. Supervisor decision: Consistently low quality responses.`);
        toast.error(`Worker ${worker.name} has been fired for poor performance`);
      } else if (newPerformance < 70 && newPerformance >= 40) {
        newStatus = 'warning';
        newLogs.push(`⚠️ Warning: Performance at ${newPerformance}%. Supervisor refining prompts...`);
      } else if (newPerformance >= 70) {
        newLogs.push(`✅ Good performance: ${newPerformance}%`);
      }

      return {
        ...worker,
        tasksCompleted: worker.tasksCompleted + 1,
        avgQuality: newQuality,
        performance: newPerformance,
        status: newStatus,
        lastTask: task.prompt.substring(0, 50) + '...',
        logs: newLogs.slice(-10), // Keep last 10 logs
      };
    });

    setWorkers(updatedWorkers);

    // Phase 4: Complete
    await new Promise(resolve => setTimeout(resolve, 500));
    const bestResult = workerResults.reduce((best, current) => 
      current.quality > best.quality ? current : best
    );
    
    updateTask(task.id, { 
      status: 'complete',
      supervisorDecision: `Selected ${bestResult.workerName}'s response (Quality: ${bestResult.quality.toFixed(1)}/10)`,
    });

    setIsRunning(false);
    toast.success('Council task completed');
  };

  const updateTask = (taskId: string, updates: Partial<CouncilTask>) => {
    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, ...updates } : t));
  };

  const handleFireWorker = (workerId: string) => {
    setWorkers(prev => prev.map(w => 
      w.id === workerId 
        ? { ...w, status: 'fired' as const, logs: [...w.logs, '🔥 Manually fired by supervisor'] }
        : w
    ));
    toast.info('Worker fired');
  };

  const handleReinstateWorker = (workerId: string) => {
    setWorkers(prev => prev.map(w => 
      w.id === workerId 
        ? { ...w, status: 'active' as const, performance: 50, logs: [...w.logs, '🔄 Reinstated - starting fresh'] }
        : w
    ));
    toast.success('Worker reinstated');
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-4">
      {/* Left: Supervisor & Task Input */}
      <div className="lg:col-span-1 space-y-4">
        <Card className="border-primary/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-primary" />
              Supervisor
            </CardTitle>
            <CardDescription>7B Model - Council Manager</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Assign Task to Council</label>
              <textarea
                value={currentTask}
                onChange={(e) => setCurrentTask(e.target.value)}
                placeholder="Enter a query for the council to research..."
                className="w-full min-h-[100px] px-3 py-2 text-sm border border-border rounded-lg bg-background resize-none"
                disabled={isRunning}
              />
            </div>
            <Button 
              onClick={handleStartTask} 
              disabled={isRunning || !currentTask.trim()}
              className="w-full"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Council Working...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 mr-2" />
                  Start Council Task
                </>
              )}
            </Button>

            <Separator />

            <div>
              <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                <Users className="w-4 h-4" />
                Active Workers: {workers.filter(w => w.status !== 'fired').length}/{workers.length}
              </h4>
              <p className="text-xs text-muted-foreground">
                Workers use SearXNG for research. Supervisor rates quality and fires poor performers.
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Recent Tasks */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Recent Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              <div className="space-y-2">
                {tasks.slice(0, 5).map(task => (
                  <div key={task.id} className="p-2 border border-border rounded text-xs space-y-1">
                    <div className="font-medium truncate">{task.prompt}</div>
                    <div className="flex items-center justify-between text-muted-foreground">
                      <span>{task.timestamp}</span>
                      <Badge variant={task.status === 'complete' ? 'default' : 'secondary'} className="text-[10px]">
                        {task.status}
                      </Badge>
                    </div>
                    {task.supervisorDecision && (
                      <div className="text-[10px] text-muted-foreground italic">
                        {task.supervisorDecision}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Middle & Right: Worker Models */}
      <div className="lg:col-span-2">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {workers.map(worker => (
            <Card key={worker.id} className={cn('relative', worker.status === 'fired' && 'opacity-60')}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-sm flex items-center gap-2">
                      {getStatusIcon(worker.status)}
                      {worker.name}
                      {worker.status === 'fired' && <Badge variant="destructive" className="text-[10px]">Fired</Badge>}
                      {worker.status === 'warning' && <Badge variant="secondary" className="text-[10px]">At Risk</Badge>}
                    </CardTitle>
                    <CardDescription className="text-xs">{worker.model}</CardDescription>
                  </div>
                  <div className={cn('text-2xl font-bold', getPerformanceColor(worker.performance))}>
                    {worker.performance}%
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-muted-foreground">Performance</span>
                    <span className={getPerformanceColor(worker.performance)}>
                      {worker.performance >= 70 ? '🟢' : worker.performance >= 40 ? '🟡' : '🔴'}
                    </span>
                  </div>
                  <Progress value={worker.performance} className="h-2" />
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <div className="text-muted-foreground">Tasks</div>
                    <div className="font-semibold">{worker.tasksCompleted}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Success</div>
                    <div className="font-semibold">{(worker.successRate * 100).toFixed(0)}%</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Quality</div>
                    <div className="font-semibold">{worker.avgQuality.toFixed(1)}/10</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Latency</div>
                    <div className="font-semibold">{worker.avgLatency.toFixed(0)}ms</div>
                  </div>
                </div>

                {worker.lastTask && (
                  <div className="text-xs">
                    <div className="text-muted-foreground">Last Task</div>
                    <div className="truncate italic">{worker.lastTask}</div>
                  </div>
                )}

                <Separator />

                <div>
                  <div className="text-xs font-semibold mb-1">Activity Log</div>
                  <ScrollArea className="h-20">
                    <div className="space-y-1 text-[10px]">
                      {worker.logs.slice(-5).reverse().map((log, idx) => (
                        <div key={idx} className="text-muted-foreground">{log}</div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>

                <div className="flex gap-2">
                  {worker.status === 'fired' ? (
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="flex-1 text-xs" 
                      onClick={() => handleReinstateWorker(worker.id)}
                    >
                      <RotateCcw className="w-3 h-3 mr-1" />
                      Reinstate
                    </Button>
                  ) : (
                    <Button 
                      size="sm" 
                      variant="destructive" 
                      className="flex-1 text-xs" 
                      onClick={() => handleFireWorker(worker.id)}
                    >
                      <X className="w-3 h-3 mr-1" />
                      Fire
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
