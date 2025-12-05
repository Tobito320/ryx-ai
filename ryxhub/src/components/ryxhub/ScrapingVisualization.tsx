import { Globe, CheckCircle2, Loader2, AlertCircle, FileText, Image, Code } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

interface ScrapedContent {
  type: "text" | "image" | "code" | "link";
  content: string;
  selector?: string;
  timestamp: string;
}

interface ScrapeProgress {
  url: string;
  status: "pending" | "scraping" | "success" | "error";
  progress: number;
  items: ScrapedContent[];
  totalItems: number;
  error?: string;
}

interface ScrapingVisualizationProps {
  scrapes: ScrapeProgress[];
}

const contentIcons = {
  text: FileText,
  image: Image,
  code: Code,
  link: Globe,
};

export function ScrapingVisualization({ scrapes }: ScrapingVisualizationProps) {
  if (scrapes.length === 0) {
    return (
      <Card className="bg-card/50 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Globe className="w-4 h-4 text-primary" />
            Scraping Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground text-sm">
            No active scraping operations
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm flex items-center gap-2">
          <Globe className="w-4 h-4 text-primary" />
          Scraping Activity
          <Badge variant="outline" className="ml-auto">
            {scrapes.length} active
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px]">
          <div className="space-y-4">
            {scrapes.map((scrape, index) => (
              <div
                key={index}
                className="p-3 rounded-lg border border-border bg-background/50"
              >
                {/* URL and Status */}
                <div className="flex items-start gap-2 mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {scrape.status === "scraping" && (
                        <Loader2 className="w-4 h-4 animate-spin text-primary" />
                      )}
                      {scrape.status === "success" && (
                        <CheckCircle2 className="w-4 h-4 text-green-500" />
                      )}
                      {scrape.status === "error" && (
                        <AlertCircle className="w-4 h-4 text-red-500" />
                      )}
                      {scrape.status === "pending" && (
                        <Loader2 className="w-4 h-4 text-muted-foreground" />
                      )}
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-xs",
                          scrape.status === "scraping" && "bg-primary/10 text-primary",
                          scrape.status === "success" && "bg-green-500/10 text-green-500",
                          scrape.status === "error" && "bg-red-500/10 text-red-500"
                        )}
                      >
                        {scrape.status}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground truncate">
                      {scrape.url}
                    </div>
                  </div>
                </div>

                {/* Progress Bar */}
                {scrape.status === "scraping" && (
                  <div className="space-y-1 mb-2">
                    <Progress value={scrape.progress} className="h-1.5" />
                    <div className="text-xs text-muted-foreground">
                      {scrape.items.length} / {scrape.totalItems} items extracted
                    </div>
                  </div>
                )}

                {/* Error Message */}
                {scrape.status === "error" && scrape.error && (
                  <div className="text-xs text-red-500 bg-red-500/10 p-2 rounded mb-2">
                    {scrape.error}
                  </div>
                )}

                {/* Scraped Items Preview */}
                {scrape.items.length > 0 && (
                  <div className="space-y-1 mt-2">
                    <div className="text-xs font-medium text-muted-foreground mb-1">
                      Extracted Content:
                    </div>
                    {scrape.items.slice(0, 3).map((item, itemIndex) => {
                      const Icon = contentIcons[item.type];
                      return (
                        <div
                          key={itemIndex}
                          className="flex items-start gap-2 p-2 rounded bg-muted/30 text-xs"
                        >
                          <Icon className="w-3 h-3 mt-0.5 flex-shrink-0 text-primary" />
                          <div className="flex-1 min-w-0">
                            <div className="font-mono text-[10px] text-muted-foreground mb-0.5">
                              {item.selector}
                            </div>
                            <div className="line-clamp-2 text-foreground">
                              {item.content}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                    {scrape.items.length > 3 && (
                      <div className="text-xs text-muted-foreground text-center py-1">
                        +{scrape.items.length - 3} more items
                      </div>
                    )}
                  </div>
                )}

                {/* Success Summary */}
                {scrape.status === "success" && (
                  <div className="text-xs text-green-500 bg-green-500/10 p-2 rounded mt-2">
                    ✓ Successfully scraped {scrape.items.length} items
                  </div>
                )}
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

// Mock data generator for testing
export function generateMockScrapes(): ScrapeProgress[] {
  return [
    {
      url: "https://example.com/article",
      status: "scraping",
      progress: 65,
      totalItems: 10,
      items: [
        {
          type: "text",
          content: "Introduction to React Flow and workflow visualization...",
          selector: "article > h1",
          timestamp: new Date().toISOString(),
        },
        {
          type: "text",
          content: "React Flow is a library for building node-based editors...",
          selector: "article > p:nth-child(2)",
          timestamp: new Date().toISOString(),
        },
        {
          type: "code",
          content: 'import ReactFlow from "reactflow";',
          selector: "pre > code",
          timestamp: new Date().toISOString(),
        },
      ],
    },
    {
      url: "https://example.com/api/data",
      status: "success",
      progress: 100,
      totalItems: 5,
      items: [
        {
          type: "text",
          content: "API endpoint documentation",
          selector: "h2",
          timestamp: new Date().toISOString(),
        },
        {
          type: "code",
          content: 'GET /api/v1/workflows',
          selector: "code.endpoint",
          timestamp: new Date().toISOString(),
        },
      ],
    },
  ];
}
