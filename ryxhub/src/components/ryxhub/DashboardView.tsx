import { Bot, Zap, Database, Activity, TrendingUp, Clock, CheckCircle, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { useRyxHub } from "@/context/RyxHubContext";
import { SearxngStatus } from "@/components/ryxhub/SearxngStatus";
import { useEffect, useState } from "react";
import { ryxService } from "@/services/ryxService";

export function DashboardView() {
  const { models, ragStatus, workflowNodes } = useRyxHub();
  const [dashboardStats, setDashboardStats] = useState<any>(null);
  const [recentActivity, setRecentActivity] = useState<any[]>([]);
  const [topWorkflows, setTopWorkflows] = useState<any[]>([]);

  // Fetch dashboard data
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Fetch stats
        const statsResponse = await fetch('http://localhost:8420/api/stats/dashboard');
        if (statsResponse.ok) {
          const data = await statsResponse.json();
          setDashboardStats(data);
        }

        // Fetch activity
        const activityResponse = await fetch('http://localhost:8420/api/activity/recent?limit=5');
        if (activityResponse.ok) {
          const data = await activityResponse.json();
          setRecentActivity(data.activities || []);
        }

        // Fetch top workflows
        const workflowsResponse = await fetch('http://localhost:8420/api/workflows/top?limit=4');
        if (workflowsResponse.ok) {
          const data = await workflowsResponse.json();
          setTopWorkflows(data.workflows || []);
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      }
    };

    fetchDashboardData();
    // Refresh every 10 seconds
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Calculate live stats from context
  const activeAgentsCount = models.filter((m) => m.status === "online").length;
  const runningWorkflows = workflowNodes.filter((n) => n.status === "running").length;

  const stats = [
    {
      title: "Active Agents",
      value: dashboardStats?.activeAgents?.value?.toString() || String(activeAgentsCount),
      change: dashboardStats?.activeAgents?.change || "+0 today",
      icon: Bot,
      color: "text-primary",
      bgColor: "bg-primary/10",
    },
    {
      title: "Workflows Running",
      value: dashboardStats?.workflowsRunning?.value?.toString() || String(runningWorkflows),
      change: `${dashboardStats?.workflowsRunning?.queued || 0} queued`,
      icon: Zap,
      color: "text-[hsl(var(--warning))]",
      bgColor: "bg-[hsl(var(--warning))]/10",
    },
    {
      title: "RAG Documents",
      value: (dashboardStats?.ragDocuments?.value || ragStatus.indexed).toLocaleString(),
      change: `+${dashboardStats?.ragDocuments?.pending || ragStatus.pending} pending`,
      icon: Database,
      color: "text-accent",
      bgColor: "bg-accent/10",
    },
    {
      title: "API Calls",
      value: dashboardStats?.apiCalls?.value || "0",
      change: dashboardStats?.apiCalls?.period || "Last 24h",
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Activity */}
          <Card className="border-border bg-card/50 backdrop-blur-sm lg:col-span-2">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                Recent Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentActivity.length > 0 ? (
                  recentActivity.map((activity) => (
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
                  ))
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <p className="text-sm">No recent activity</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* SearXNG Status */}
          <SearxngStatus />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
                {topWorkflows.length > 0 ? (
                  topWorkflows.map((workflow) => (
                    <div key={workflow.name} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-foreground">{workflow.name}</span>
                        <span className="text-xs text-muted-foreground">
                          {workflow.runs} runs • {workflow.successRate}% success
                        </span>
                      </div>
                      <Progress value={workflow.successRate} className="h-2" />
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <p className="text-sm">No workflows yet</p>
                    <p className="text-xs mt-1">Create your first workflow to get started</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
