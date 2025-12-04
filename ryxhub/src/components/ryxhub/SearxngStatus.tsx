import { useState, useEffect } from "react";
import { Search, CheckCircle, XCircle, Loader2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ryxService } from "@/services/ryxService";
import { toast } from "sonner";

export function SearxngStatus() {
  const [status, setStatus] = useState<{
    healthy: boolean;
    status: string;
    message: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    checkStatus();
  }, []);

  const checkStatus = async () => {
    setLoading(true);
    try {
      const result = await ryxService.getSearxngStatus();
      setStatus(result);
    } catch (error) {
      console.error("Failed to check SearXNG status:", error);
      setStatus({
        healthy: false,
        status: "error",
        message: "Failed to connect to SearXNG service",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTestSearch = async () => {
    setLoading(true);
    try {
      const result = await ryxService.searxngSearch("test query");
      if (result.results && result.results.length > 0) {
        toast.success("SearXNG is working!", {
          description: `Found ${result.total} results`,
        });
      } else {
        toast.warning("SearXNG responded but returned no results");
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Unknown error";
      toast.error("Search failed", { description: errorMessage });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-border bg-card/50 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-semibold flex items-center gap-2">
          <Search className="w-4 h-4" />
          SearXNG Search
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border">
          <div className="flex items-center gap-2">
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            ) : status?.healthy ? (
              <CheckCircle className="w-4 h-4 text-[hsl(var(--success))]" />
            ) : (
              <XCircle className="w-4 h-4 text-destructive" />
            )}
            <div>
              <p className="text-sm font-medium text-foreground">
                {status?.healthy ? "Online" : "Offline"}
              </p>
              <p className="text-xs text-muted-foreground">
                {status?.message || "Checking status..."}
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={checkStatus}
            disabled={loading}
          >
            Refresh
          </Button>
        </div>

        <Button
          onClick={handleTestSearch}
          disabled={loading || !status?.healthy}
          className="w-full"
          size="sm"
          variant="secondary"
        >
          {loading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
          Test Search
        </Button>
      </CardContent>
    </Card>
  );
}
