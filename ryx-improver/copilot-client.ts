import Anthropic from "@anthropic-ai/sdk";
import OpenAI from "openai";
import { MODELS, ModelType } from "./models";

/**
 * GitHub Copilot Pro+ Client
 * Uses GitHub's API to access various AI models
 */
export class CopilotClient {
  private anthropic: Anthropic;
  private openai: OpenAI;
  private creditsUsed = 0;

  constructor() {
    const apiKey = process.env.GITHUB_TOKEN;
    
    if (!apiKey) {
      throw new Error("GITHUB_TOKEN environment variable is required");
    }

    // GitHub Copilot uses different base URLs for different model providers
    this.anthropic = new Anthropic({
      apiKey: apiKey,
      baseURL: "https://models.inference.ai.azure.com",
    });

    this.openai = new OpenAI({
      apiKey: apiKey,
      baseURL: "https://models.inference.ai.azure.com",
    });
  }

  async generate(
    request: string,
    modelType: ModelType = "coding",
    systemPrompt?: string
  ): Promise<string> {
    const config = MODELS[modelType];
    const isClaudeModel = config.model.includes("claude");

    try {
      console.log(`\n📝 Generating with ${modelType} (${config.model})...`);

      let result: string;

      if (isClaudeModel) {
        // Use Anthropic client for Claude models
        const response = await this.anthropic.messages.create({
          model: config.model,
          max_tokens: config.maxTokens,
          system: systemPrompt,
          messages: [
            {
              role: "user",
              content: request,
            },
          ],
        });

        result = response.content[0].type === "text" 
          ? response.content[0].text 
          : "";
      } else {
        // Use OpenAI client for GPT models
        const messages: OpenAI.ChatCompletionMessageParam[] = [];
        
        if (systemPrompt) {
          messages.push({ role: "system", content: systemPrompt });
        }
        messages.push({ role: "user", content: request });

        const response = await this.openai.chat.completions.create({
          model: config.model,
          max_tokens: config.maxTokens,
          messages,
        });

        result = response.choices[0]?.message?.content || "";
      }

      this.creditsUsed += config.cost;

      console.log(`✅ Generated with ${config.model} (+${config.cost} credits)`);
      console.log(`📊 Total credits used this session: ${this.creditsUsed}`);

      return result;
    } catch (error: any) {
      console.error(`❌ Generation failed: ${error.message}`);
      throw error;
    }
  }

  /**
   * Generate with JSON output
   */
  async generateJSON<T = any>(
    request: string,
    modelType: ModelType = "coding"
  ): Promise<T> {
    const prompt = `${request}

IMPORTANT: Return ONLY valid JSON, no markdown code blocks, no explanation.`;

    const response = await this.generate(prompt, modelType);
    
    // Extract JSON from response (handle markdown code blocks)
    let jsonStr = response.trim();
    if (jsonStr.startsWith("```json")) {
      jsonStr = jsonStr.slice(7);
    }
    if (jsonStr.startsWith("```")) {
      jsonStr = jsonStr.slice(3);
    }
    if (jsonStr.endsWith("```")) {
      jsonStr = jsonStr.slice(0, -3);
    }
    
    return JSON.parse(jsonStr.trim());
  }

  getCreditsUsed(): number {
    return this.creditsUsed;
  }

  resetCredits(): void {
    this.creditsUsed = 0;
  }
}

export default CopilotClient;
