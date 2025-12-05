import { FileText, Code, Shield, MessageSquare, Database, GitBranch } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { WorkflowNode, Connection } from "@/types/ryxhub";

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: React.ComponentType<{ className?: string }>;
  nodes: Omit<WorkflowNode, "logs" | "runs">[];
  connections: Connection[];
  tags: string[];
}

interface WorkflowTemplatesProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectTemplate: (template: WorkflowTemplate) => void;
}

// n8n-inspired workflow templates
export const workflowTemplates: WorkflowTemplate[] = [
  {
    id: "code-review",
    name: "AI Code Review",
    description: "Automatically review code changes with multiple AI agents for quality, security, and best practices",
    category: "Development",
    icon: Code,
    tags: ["code", "review", "quality"],
    nodes: [
      {
        id: "trigger-1",
        type: "trigger",
        name: "Git Push",
        x: 100,
        y: 200,
        status: "idle",
        config: { triggerType: "webhook" },
      },
      {
        id: "agent-1",
        type: "agent",
        name: "Code Quality Check",
        x: 350,
        y: 100,
        status: "idle",
        config: {
          model: "/models/medium/coding/qwen2.5-coder-7b-gptq",
          prompt: "Review this code for quality issues, code smells, and improvement suggestions. Check for: naming conventions, code duplication, complexity, error handling, and performance issues.",
        },
      },
      {
        id: "agent-2",
        type: "agent",
        name: "Security Audit",
        x: 350,
        y: 250,
        status: "idle",
        config: {
          model: "/models/medium/coding/qwen2.5-coder-7b-gptq",
          prompt: "Analyze this code for security vulnerabilities including: SQL injection, XSS, CSRF, hardcoded secrets, insecure authentication, and OWASP Top 10 issues. Provide severity ratings and fix recommendations.",
        },
      },
      {
        id: "tool-1",
        type: "tool",
        name: "Aggregate Results",
        x: 600,
        y: 175,
        status: "idle",
        config: { toolType: "aggregate" },
      },
      {
        id: "output-1",
        type: "output",
        name: "Create PR Comment",
        x: 850,
        y: 175,
        status: "idle",
        config: { format: "markdown", destination: "github-pr" },
      },
    ],
    connections: [
      { id: "conn-1", from: "trigger-1", to: "agent-1" },
      { id: "conn-2", from: "trigger-1", to: "agent-2" },
      { id: "conn-3", from: "agent-1", to: "tool-1" },
      { id: "conn-4", from: "agent-2", to: "tool-1" },
      { id: "conn-5", from: "tool-1", to: "output-1" },
    ],
  },
  {
    id: "documentation-generator",
    name: "Documentation Generator",
    description: "Generate comprehensive documentation from codebase with RAG-enhanced context",
    category: "Documentation",
    icon: FileText,
    tags: ["docs", "markdown", "rag"],
    nodes: [
      {
        id: "trigger-1",
        type: "trigger",
        name: "Manual Trigger",
        x: 100,
        y: 200,
        status: "idle",
        config: { triggerType: "manual" },
      },
      {
        id: "tool-1",
        type: "tool",
        name: "Scan Codebase",
        x: 350,
        y: 200,
        status: "idle",
        config: { toolType: "filesystem" },
      },
      {
        id: "tool-2",
        type: "tool",
        name: "RAG Context",
        x: 600,
        y: 200,
        status: "idle",
        config: { toolType: "rag" },
      },
      {
        id: "agent-1",
        type: "agent",
        name: "Generate Docs",
        x: 850,
        y: 200,
        status: "idle",
        config: {
          model: "/models/medium/coding/qwen2.5-coder-7b-gptq",
          prompt: "Generate comprehensive API documentation from the provided code. Include: function signatures, parameters, return types, usage examples, and any important notes about behavior or limitations.",
        },
      },
      {
        id: "output-1",
        type: "output",
        name: "Save Markdown",
        x: 1100,
        y: 200,
        status: "idle",
        config: { format: "markdown", destination: "docs/README.md" },
      },
    ],
    connections: [
      { id: "conn-1", from: "trigger-1", to: "tool-1" },
      { id: "conn-2", from: "tool-1", to: "tool-2" },
      { id: "conn-3", from: "tool-2", to: "agent-1" },
      { id: "conn-4", from: "agent-1", to: "output-1" },
    ],
  },
  {
    id: "research-assistant",
    name: "Research Assistant",
    description: "Multi-source research workflow with web search, scraping, and intelligent synthesis",
    category: "Research",
    icon: MessageSquare,
    tags: ["research", "websearch", "scrape"],
    nodes: [
      {
        id: "trigger-1",
        type: "trigger",
        name: "Research Query",
        x: 100,
        y: 200,
        status: "idle",
        config: { triggerType: "manual" },
      },
      {
        id: "tool-1",
        type: "tool",
        name: "Web Search",
        x: 350,
        y: 100,
        status: "idle",
        config: { toolType: "websearch" },
      },
      {
        id: "tool-2",
        type: "tool",
        name: "Scrape Results",
        x: 350,
        y: 250,
        status: "idle",
        config: { toolType: "scrape" },
      },
      {
        id: "tool-3",
        type: "tool",
        name: "RAG Lookup",
        x: 350,
        y: 350,
        status: "idle",
        config: { toolType: "rag" },
      },
      {
        id: "agent-1",
        type: "agent",
        name: "Synthesize Research",
        x: 600,
        y: 225,
        status: "idle",
        config: {
          model: "/models/medium/general/qwen2.5-7b-gptq",
          prompt: "Synthesize all research findings into a comprehensive summary. Organize by themes, cite all sources, highlight key insights, note conflicting information, and suggest areas for further research.",
        },
      },
      {
        id: "output-1",
        type: "output",
        name: "Generate Report",
        x: 850,
        y: 225,
        status: "idle",
        config: { format: "markdown", destination: "research-report.md" },
      },
    ],
    connections: [
      { id: "conn-1", from: "trigger-1", to: "tool-1" },
      { id: "conn-2", from: "trigger-1", to: "tool-2" },
      { id: "conn-3", from: "trigger-1", to: "tool-3" },
      { id: "conn-4", from: "tool-1", to: "agent-1" },
      { id: "conn-5", from: "tool-2", to: "agent-1" },
      { id: "conn-6", from: "tool-3", to: "agent-1" },
      { id: "conn-7", from: "agent-1", to: "output-1" },
    ],
  },
  {
    id: "data-pipeline",
    name: "Data Processing Pipeline",
    description: "Extract, transform, and load data with conditional branching and error handling",
    category: "Data",
    icon: Database,
    tags: ["etl", "data", "pipeline"],
    nodes: [
      {
        id: "trigger-1",
        type: "trigger",
        name: "Scheduled Run",
        x: 100,
        y: 200,
        status: "idle",
        config: { triggerType: "schedule", cron: "0 0 * * *" },
      },
      {
        id: "tool-1",
        type: "tool",
        name: "Fetch Data",
        x: 350,
        y: 200,
        status: "idle",
        config: { toolType: "websearch" },
      },
      {
        id: "agent-1",
        type: "agent",
        name: "Transform Data",
        x: 600,
        y: 200,
        status: "idle",
        config: {
          model: "/models/medium/coding/qwen2.5-coder-7b-gptq",
          prompt: "Transform and clean the data: normalize formats, handle missing values, remove duplicates, validate data types, and apply business rules. Document all transformations applied.",
        },
      },
      {
        id: "output-1",
        type: "output",
        name: "Save to Database",
        x: 850,
        y: 200,
        status: "idle",
        config: { format: "json", destination: "database" },
      },
    ],
    connections: [
      { id: "conn-1", from: "trigger-1", to: "tool-1" },
      { id: "conn-2", from: "tool-1", to: "agent-1" },
      { id: "conn-3", from: "agent-1", to: "output-1" },
    ],
  },
  {
    id: "security-scanner",
    name: "Security Scanner",
    description: "Comprehensive security scanning with vulnerability detection and automated fixes",
    category: "Security",
    icon: Shield,
    tags: ["security", "vulnerabilities", "fixes"],
    nodes: [
      {
        id: "trigger-1",
        type: "trigger",
        name: "PR Opened",
        x: 100,
        y: 200,
        status: "idle",
        config: { triggerType: "webhook" },
      },
      {
        id: "tool-1",
        type: "tool",
        name: "Scan Code",
        x: 350,
        y: 200,
        status: "idle",
        config: { toolType: "filesystem" },
      },
      {
        id: "agent-1",
        type: "agent",
        name: "Detect Vulnerabilities",
        x: 600,
        y: 150,
        status: "idle",
        config: {
          model: "/models/medium/coding/qwen2.5-coder-7b-gptq",
          prompt: "Perform deep security analysis: scan for OWASP Top 10 vulnerabilities, check for exposed secrets, review authentication/authorization logic, and identify potential attack vectors.",
        },
      },
      {
        id: "agent-2",
        type: "agent",
        name: "Generate Fixes",
        x: 600,
        y: 250,
        status: "idle",
        config: {
          model: "/models/medium/coding/qwen2.5-coder-7b-gptq",
          prompt: "Generate secure code fixes for each identified vulnerability. Provide: the fix code, explanation of why it's more secure, and any additional security recommendations.",
        },
      },
      {
        id: "output-1",
        type: "output",
        name: "Create Report",
        x: 850,
        y: 200,
        status: "idle",
        config: { format: "markdown", destination: "security-report.md" },
      },
    ],
    connections: [
      { id: "conn-1", from: "trigger-1", to: "tool-1" },
      { id: "conn-2", from: "tool-1", to: "agent-1" },
      { id: "conn-3", from: "agent-1", to: "agent-2" },
      { id: "conn-4", from: "agent-2", to: "output-1" },
    ],
  },
  {
    id: "test-generator",
    name: "Test Suite Generator",
    description: "Automatically generate comprehensive test suites with edge cases and mocks",
    category: "Testing",
    icon: GitBranch,
    tags: ["testing", "unit-tests", "automation"],
    nodes: [
      {
        id: "trigger-1",
        type: "trigger",
        name: "Code Commit",
        x: 100,
        y: 200,
        status: "idle",
        config: { triggerType: "webhook" },
      },
      {
        id: "tool-1",
        type: "tool",
        name: "Analyze Code",
        x: 350,
        y: 200,
        status: "idle",
        config: { toolType: "filesystem" },
      },
      {
        id: "agent-1",
        type: "agent",
        name: "Generate Tests",
        x: 600,
        y: 200,
        status: "idle",
        config: {
          model: "/models/medium/coding/qwen2.5-coder-7b-gptq",
          prompt: "Generate comprehensive unit tests: cover happy paths, edge cases, error conditions, and boundary values. Include mocks for external dependencies and clear test descriptions.",
        },
      },
      {
        id: "output-1",
        type: "output",
        name: "Save Tests",
        x: 850,
        y: 200,
        status: "idle",
        config: { format: "text", destination: "tests/" },
      },
    ],
    connections: [
      { id: "conn-1", from: "trigger-1", to: "tool-1" },
      { id: "conn-2", from: "tool-1", to: "agent-1" },
      { id: "conn-3", from: "agent-1", to: "output-1" },
    ],
  },
];

export function WorkflowTemplates({ open, onOpenChange, onSelectTemplate }: WorkflowTemplatesProps) {
  const categories = Array.from(new Set(workflowTemplates.map((t) => t.category)));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Workflow Templates</DialogTitle>
          <DialogDescription>
            Choose from pre-built workflows inspired by n8n best practices
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[60vh] pr-4">
          <div className="space-y-6">
            {categories.map((category) => (
              <div key={category}>
                <h3 className="text-sm font-semibold mb-3 text-muted-foreground">{category}</h3>
                <div className="grid grid-cols-2 gap-4">
                  {workflowTemplates
                    .filter((t) => t.category === category)
                    .map((template) => {
                      const Icon = template.icon;
                      return (
                        <Card
                          key={template.id}
                          className="cursor-pointer hover:border-primary transition-all"
                          onClick={() => {
                            onSelectTemplate(template);
                            onOpenChange(false);
                          }}
                        >
                          <CardHeader className="pb-3">
                            <div className="flex items-start gap-3">
                              <div className="p-2 rounded-lg bg-primary/10">
                                <Icon className="w-5 h-5 text-primary" />
                              </div>
                              <div className="flex-1">
                                <CardTitle className="text-sm">{template.name}</CardTitle>
                                <CardDescription className="text-xs mt-1">
                                  {template.nodes.length} nodes • {template.connections.length} connections
                                </CardDescription>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <p className="text-xs text-muted-foreground mb-3">
                              {template.description}
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {template.tags.map((tag) => (
                                <Badge key={tag} variant="secondary" className="text-xs px-2 py-0">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
