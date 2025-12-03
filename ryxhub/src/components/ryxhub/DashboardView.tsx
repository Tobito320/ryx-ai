import { Bot, Zap, Database, Activity, TrendingUp, Clock, CheckCircle, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useRyxHub } from "@/context/RyxHubContext";
import { mockDashboardStats, mockRecentActivity, mockTopWorkflows } from "@/data/mockData";

export function DashboardView() {
  const { models, ragStatus, workflowNodes } = useRyxHub();

  // Calculate live stats from context
  const activeAgentsCount = models.filter((m) => m.status === "online").length;
  const runningWorkflows = workflowNodes.filter((n) => n.status === "running").length;

  const stats = [
    {
      title: "Active Agents",
      value: String(activeAgentsCount),
      change: mockDashboardStats.activeAgents.change,
      icon: Bot,
      color: "text-primary",
      bgColor: "bg-primary/10",
    },
    {
      title: "Workflows Running",
      value: String(runningWorkflows),
      change: `${mockDashboardStats.workflowsRunning.queued} queued`,
      icon: Zap,
      color: "text-[hsl(var(--warning))]",
      bgColor: "bg-[hsl(var(--warning))]/10",
    },
    {
      title: "RAG Documents",
      value: ragStatus.indexed.toLocaleString(),
      change: `+${ragStatus.pending} pending`,
      icon: Database,
      color: "text-accent",
      bgColor: "bg-accent/10",
    },
    {
      title: "API Calls",
      value: mockDashboardStats.apiCalls.value,
      change: mockDashboardStats.apiCalls.period,
      icon: Activity,
      color: "text-[hsl(var(--success))]",
      bgColor: "bg-[hsl(var(--success))]/10",
    },
  ];

  const getActivityIcon = (type: string) => {
    switch (type) {
      case "success":
        return <CheckCircle className="w-4 h-4 text-[hsl(var(--success))]" />;
      case "warning":
        return <AlertTriangle className="w-4 h-4 text-[hsl(var(--warning))]" />;
      default:
        return <Activity className="w-4 h-4 text-primary" />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-background overflow-auto">
      {/* Header */}
      <div className="px-8 py-6 border-b border-border bg-card/50 backdrop-blur-sm">
        <h1 className="text-2xl font-bold text-foreground">Welcome back</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Here's what's happening with your AI workflows today
        </p>
      </div>

      <div className="p-8 space-y-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <Card key={stat.title} className="border-border bg-card/50 backdrop-blur-sm hover:bg-card/70 transition-colors">
                <CardContent className="p-5">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                        {stat.title}
                      </p>
                      <p className="text-3xl font-bold text-foreground mt-1">{stat.value}</p>
                      <p className="text-xs text-muted-foreground mt-1">{stat.change}</p>
                    </div>
                    <div className={`w-12 h-12 rounded-xl ${stat.bgColor} flex items-center justify-center`}>
                      <Icon className={`w-6 h-6 ${stat.color}`} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Activity */}
          <Card className="border-border bg-card/50 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {mockRecentActivity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center gap-3 p-3 rounded-lg bg-muted/30 border border-border hover:bg-muted/50 transition-colors"
                  >
                    {getActivityIcon(activity.type)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-foreground truncate">{activity.message}</p>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">{activity.time}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Top Workflows */}
          <Card className="border-border bg-card/50 backdrop-blur-sm">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-muted-foreground" />
                Top Workflows
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockTopWorkflows.map((workflow) => (
                  <div key={workflow.name} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-foreground">{workflow.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {workflow.runs} runs • {workflow.successRate}% success
                      </span>
                    </div>
                    <Progress value={workflow.successRate} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
