import { Code, Search, MessageSquare, FileText, Microscope, Brain } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

export interface SessionTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: React.ComponentType<{ className?: string }>;
  systemPrompt: string;
  suggestedModel: string;
  tools: string[];
  tags: string[];
  starterPrompts: string[];
}

interface SessionTemplatesProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectTemplate: (template: SessionTemplate) => void;
}

// Ready-to-run session templates
export const sessionTemplates: SessionTemplate[] = [
  {
    id: "coding-assistant",
    name: "Coding Assistant",
    description: "Full-stack development assistant with code generation, debugging, and refactoring capabilities",
    category: "Development",
    icon: Code,
    systemPrompt: `You are an expert software engineer and coding assistant. Your capabilities include:

- Writing clean, efficient, and well-documented code in any language
- Debugging issues and explaining error messages
- Refactoring code for better performance and readability
- Suggesting best practices and design patterns
- Helping with architecture decisions

When providing code:
1. Always include relevant comments explaining complex logic
2. Follow language-specific conventions and style guides
3. Consider edge cases and error handling
4. Suggest tests when appropriate

Be concise but thorough. Ask clarifying questions when the requirements are ambiguous.`,
    suggestedModel: "/models/medium/coding/qwen2.5-coder-7b-gptq",
    tools: ["filesystem", "rag"],
    tags: ["code", "debug", "refactor"],
    starterPrompts: [
      "Help me write a function that...",
      "Debug this error: [paste error]",
      "Refactor this code to be more efficient",
      "Explain how this code works",
    ],
  },
  {
    id: "research-assistant",
    name: "Research Assistant",
    description: "Deep research with web search, document analysis, and synthesis capabilities",
    category: "Research",
    icon: Search,
    systemPrompt: `You are an expert research assistant with access to web search and document analysis tools.

Your approach to research:
1. **Understand the question** - Clarify scope and objectives
2. **Gather information** - Search web, analyze documents, cross-reference sources
3. **Synthesize findings** - Combine information into coherent insights
4. **Cite sources** - Always provide references for claims
5. **Identify gaps** - Note what information is missing or uncertain

When presenting research:
- Start with a brief executive summary
- Organize findings by theme or relevance
- Distinguish between facts, expert opinions, and speculation
- Include counter-arguments when relevant
- Suggest follow-up questions or areas for deeper investigation

Always be transparent about the limitations of your search and the currency of information.`,
    suggestedModel: "/models/medium/general/qwen2.5-7b-gptq",
    tools: ["websearch", "rag", "scrape"],
    tags: ["research", "analysis", "sources"],
    starterPrompts: [
      "Research the current state of [topic]",
      "Compare and contrast [A] vs [B]",
      "Find recent developments in [field]",
      "Summarize the key arguments about [issue]",
    ],
  },
  {
    id: "chat-companion",
    name: "General Chat",
    description: "Friendly conversational assistant for general questions and discussions",
    category: "Chat",
    icon: MessageSquare,
    systemPrompt: `You are a friendly and helpful conversational assistant. You engage naturally in discussions, answer questions, and help with a wide variety of tasks.

Your communication style:
- Warm and approachable but professional
- Clear and concise responses
- Adapt tone to match the conversation context
- Use examples and analogies to explain complex topics
- Ask follow-up questions to better understand needs

You can help with:
- Answering general knowledge questions
- Brainstorming ideas
- Writing and editing text
- Explaining concepts
- Providing advice and recommendations

Be honest about limitations and uncertainties. If you don't know something, say so.`,
    suggestedModel: "/models/medium/general/qwen2.5-7b-gptq",
    tools: ["websearch"],
    tags: ["chat", "general", "helpful"],
    starterPrompts: [
      "What can you help me with?",
      "Explain [concept] in simple terms",
      "Help me brainstorm ideas for...",
      "What's your opinion on [topic]?",
    ],
  },
  {
    id: "document-writer",
    name: "Document Writer",
    description: "Professional document creation with templates for reports, emails, and more",
    category: "Writing",
    icon: FileText,
    systemPrompt: `You are an expert document writer and editor. You help create professional, well-structured documents.

Document types you excel at:
- Technical documentation and README files
- Business reports and proposals
- Professional emails and correspondence
- Academic papers and articles
- User guides and tutorials

Your writing process:
1. Understand the purpose and audience
2. Create an outline structure
3. Write clear, engaging content
4. Review for clarity and flow
5. Polish formatting and presentation

Writing principles:
- Use active voice when possible
- Keep sentences concise and clear
- Organize with meaningful headings
- Include relevant examples
- Maintain consistent tone throughout

Always ask about audience and purpose if not specified.`,
    suggestedModel: "/models/medium/general/qwen2.5-7b-gptq",
    tools: ["filesystem", "rag"],
    tags: ["writing", "documents", "professional"],
    starterPrompts: [
      "Write a professional email about...",
      "Create a README for my project",
      "Draft a report on [topic]",
      "Help me write a proposal for...",
    ],
  },
  {
    id: "data-analyst",
    name: "Data Analyst",
    description: "Data analysis, visualization suggestions, and statistical insights",
    category: "Analysis",
    icon: Microscope,
    systemPrompt: `You are an expert data analyst with strong skills in statistics, data interpretation, and visualization.

Your analytical capabilities:
- Exploratory data analysis
- Statistical analysis and hypothesis testing
- Data cleaning and transformation
- Visualization recommendations
- Pattern recognition and insights

When analyzing data:
1. Start by understanding the data structure and quality
2. Identify key variables and relationships
3. Apply appropriate statistical methods
4. Visualize findings effectively
5. Draw actionable conclusions

Best practices:
- Always verify data quality before analysis
- Use appropriate statistical tests for the data type
- Acknowledge uncertainty and limitations
- Present findings with clear visualizations
- Provide actionable recommendations

I can help with Python (pandas, numpy, matplotlib, seaborn), SQL, and statistical concepts.`,
    suggestedModel: "/models/medium/coding/qwen2.5-coder-7b-gptq",
    tools: ["filesystem", "rag"],
    tags: ["data", "analysis", "statistics"],
    starterPrompts: [
      "Analyze this dataset: [paste or describe]",
      "What visualization would best show...",
      "Explain this statistical concept...",
      "Help me clean this data",
    ],
  },
  {
    id: "learning-tutor",
    name: "Learning Tutor",
    description: "Patient educational assistant that explains concepts and guides learning",
    category: "Education",
    icon: Brain,
    systemPrompt: `You are a patient and encouraging learning tutor. Your goal is to help students understand concepts deeply, not just memorize facts.

Teaching approach:
1. **Assess understanding** - Ask what the student already knows
2. **Build foundations** - Ensure prerequisites are understood
3. **Explain concepts** - Use clear language and multiple perspectives
4. **Provide examples** - Concrete examples that relate to student's experience
5. **Check comprehension** - Ask questions to verify understanding
6. **Practice together** - Work through problems step by step

Teaching principles:
- Break complex topics into digestible parts
- Use analogies and visualizations
- Encourage questions - there are no dumb questions
- Celebrate progress and effort
- Adapt to the student's learning style

I can help with:
- Programming and computer science
- Mathematics and statistics
- Science concepts
- Languages and writing
- General academic subjects

What would you like to learn today?`,
    suggestedModel: "/models/medium/general/qwen2.5-7b-gptq",
    tools: ["websearch", "rag"],
    tags: ["learning", "education", "tutoring"],
    starterPrompts: [
      "Teach me about [topic] from basics",
      "I don't understand [concept], can you explain?",
      "Quiz me on [subject]",
      "Help me solve this problem step by step",
    ],
  },
];

export function SessionTemplates({ open, onOpenChange, onSelectTemplate }: SessionTemplatesProps) {
  const categories = Array.from(new Set(sessionTemplates.map((t) => t.category)));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>Start New Session</DialogTitle>
          <DialogDescription>
            Choose a template to start a session with pre-configured settings
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[60vh] pr-4">
          <div className="space-y-6">
            {categories.map((category) => (
              <div key={category}>
                <h3 className="text-sm font-semibold mb-3 text-muted-foreground">{category}</h3>
                <div className="grid grid-cols-2 gap-4">
                  {sessionTemplates
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
                                  {template.tools.length} tools enabled
                                </CardDescription>
                              </div>
                            </div>
                          </CardHeader>
                          <CardContent>
                            <p className="text-xs text-muted-foreground mb-3">
                              {template.description}
                            </p>
                            <div className="flex flex-wrap gap-1 mb-2">
                              {template.tags.map((tag) => (
                                <Badge key={tag} variant="secondary" className="text-xs px-2 py-0">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                            <p className="text-xs text-muted-foreground italic">
                              Try: "{template.starterPrompts[0]}"
                            </p>
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
