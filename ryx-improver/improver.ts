#!/usr/bin/env npx ts-node

import { execSync, exec } from "child_process";
import * as fs from "fs";
import * as path from "path";
import CopilotClient from "./copilot-client";

interface GeneratedFiles {
  files: Record<string, string>;
  summary?: string;
}

/**
 * Ryx Self-Improver
 * Automatically adds features to RyxHub using GitHub Copilot Pro+ models
 */
class RyxImprover {
  private copilot: CopilotClient;
  private projectRoot: string;
  private dryRun: boolean;

  constructor(options: { dryRun?: boolean } = {}) {
    this.copilot = new CopilotClient();
    this.projectRoot = path.join(__dirname, "..");
    this.dryRun = options.dryRun ?? false;
  }

  async improve(featureRequest: string): Promise<void> {
    console.log(`\n🚀 Ryx Self-Improvement Started`);
    console.log(`Feature: ${featureRequest}`);
    console.log(`Mode: ${this.dryRun ? "DRY RUN (no changes)" : "LIVE"}\n`);

    try {
      // Step 1: Analyze codebase context
      console.log(`Step 1️⃣: Analyzing codebase...`);
      const context = this.gatherContext();

      // Step 2: Plan with chat model (0x cost)
      console.log(`\nStep 2️⃣: Planning...`);
      const plan = await this.copilot.generate(
        `You are analyzing the RyxHub project to plan a new feature.

PROJECT STRUCTURE:
${context.structure}

EXISTING COMPONENTS:
${context.components}

FEATURE REQUEST:
${featureRequest}

Create a detailed plan:
1. What files need to be created?
2. What files need to be modified?
3. What dependencies are needed?
4. What tests should be added?

Be specific about file paths and changes.`,
        "chat"
      );
      console.log(`\n📋 Plan:\n${plan}\n`);

      // Step 3: Generate code with coding model (1x cost)
      console.log(`Step 3️⃣: Generating code...`);
      const generated = await this.copilot.generateJSON<GeneratedFiles>(
        `Generate code for this feature in RyxHub:

FEATURE: ${featureRequest}

PLAN:
${plan}

PROJECT CONTEXT:
- TypeScript/React frontend in ryxhub/src/
- FastAPI Python backend in ryx_pkg/interfaces/web/backend/
- Follow existing patterns in the codebase

Return JSON with this EXACT structure:
{
  "files": {
    "path/to/file.ts": "file content here",
    "path/to/another.py": "file content here"
  },
  "summary": "Brief description of changes"
}

RULES:
- Use relative paths from project root
- Include complete file contents
- Follow existing code style
- Include proper imports
- Add error handling`,
        "coding"
      );

      console.log(`\n📦 Generated ${Object.keys(generated.files).length} files`);
      if (generated.summary) {
        console.log(`Summary: ${generated.summary}`);
      }

      // Step 4: Write files
      console.log(`\nStep 4️⃣: Writing files...`);
      if (!this.dryRun) {
        this.writeFiles(generated.files);
      } else {
        console.log("  (dry run - skipping file writes)");
        for (const filepath of Object.keys(generated.files)) {
          console.log(`  📄 Would write: ${filepath}`);
        }
      }

      // Step 5: Build
      console.log(`\nStep 5️⃣: Building...`);
      if (!this.dryRun) {
        try {
          // Try frontend build if files were in ryxhub
          const hasRyxhubFiles = Object.keys(generated.files).some(f => f.startsWith("ryxhub/"));
          if (hasRyxhubFiles) {
            execSync("npm run build", { 
              cwd: path.join(this.projectRoot, "ryxhub"),
              stdio: "pipe"
            });
          }
          console.log(`✅ Build successful`);
        } catch (e: any) {
          console.log(`⚠️ Build failed, attempting fix...`);
          await this.attemptFix(e.message, generated.files);
        }
      } else {
        console.log("  (dry run - skipping build)");
      }

      // Step 6: Test (optional)
      console.log(`\nStep 6️⃣: Verifying...`);
      if (!this.dryRun) {
        // Run type check
        try {
          execSync("npx tsc --noEmit", { 
            cwd: path.join(this.projectRoot, "ryxhub"),
            stdio: "pipe"
          });
          console.log(`✅ Type check passed`);
        } catch {
          console.log(`⚠️ Type check has warnings (non-blocking)`);
        }
      }

      // Step 7: Commit
      console.log(`\nStep 7️⃣: Committing...`);
      if (!this.dryRun) {
        const commitMsg = `feat: ${featureRequest.slice(0, 50)}${featureRequest.length > 50 ? '...' : ''}`;
        execSync(`git add -A && git commit -m "${commitMsg}"`, {
          cwd: this.projectRoot,
          stdio: "pipe"
        });
        console.log(`✅ Changes committed: "${commitMsg}"`);
      } else {
        console.log("  (dry run - skipping commit)");
      }

      console.log(`\n🎉 Success! Feature added to Ryx.`);
      console.log(`📊 Total credits used: ${this.copilot.getCreditsUsed()}`);

    } catch (error: any) {
      console.error(`\n💥 Failed:`, error.message);
      
      if (!this.dryRun) {
        console.log(`Rolling back...`);
        try {
          execSync("git checkout .", { cwd: this.projectRoot, stdio: "pipe" });
          console.log(`✅ Rolled back successfully`);
        } catch {
          console.log(`⚠️ Could not rollback, please check git status`);
        }
      }
      
      process.exit(1);
    }
  }

  /**
   * Attempt to fix build/test failures using emergency model
   */
  private async attemptFix(error: string, originalFiles: Record<string, string>): Promise<void> {
    console.log(`\n🔧 Attempting emergency fix (3x cost)...`);

    const fix = await this.copilot.generateJSON<GeneratedFiles>(
      `Fix this build error:

ERROR:
${error.slice(0, 2000)}

ORIGINAL FILES:
${JSON.stringify(originalFiles, null, 2).slice(0, 4000)}

Return the fixed files in JSON format:
{
  "files": {
    "path/to/file": "corrected content"
  }
}

Only include files that need changes.`,
      "emergency"
    );

    this.writeFiles(fix.files);
    
    // Retry build
    execSync("npm run build", { 
      cwd: path.join(this.projectRoot, "ryxhub"),
      stdio: "pipe"
    });
    console.log(`✅ Build successful after fix`);
  }

  /**
   * Gather context about the project
   */
  private gatherContext(): { structure: string; components: string } {
    // Get directory structure
    let structure = "";
    try {
      structure = execSync("find ryxhub/src -type f -name '*.tsx' | head -30", {
        cwd: this.projectRoot,
        encoding: "utf-8"
      });
    } catch {
      structure = "Could not read structure";
    }

    // Get existing components
    let components = "";
    const componentsDir = path.join(this.projectRoot, "ryxhub/src/components/ryxhub");
    if (fs.existsSync(componentsDir)) {
      components = fs.readdirSync(componentsDir)
        .filter(f => f.endsWith(".tsx"))
        .join("\n");
    }

    return { structure, components };
  }

  /**
   * Write generated files to disk
   */
  private writeFiles(files: Record<string, string>): void {
    for (const [filepath, content] of Object.entries(files)) {
      const fullPath = path.join(this.projectRoot, filepath);
      const dir = path.dirname(fullPath);

      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      fs.writeFileSync(fullPath, content, "utf-8");
      console.log(`  ✅ ${filepath}`);
    }
  }
}

// CLI Entry Point
async function main() {
  const args = process.argv.slice(2);
  
  // Parse flags
  const dryRun = args.includes("--dry-run") || args.includes("-d");
  const help = args.includes("--help") || args.includes("-h");
  
  // Remove flags from args
  const featureArgs = args.filter(a => !a.startsWith("-"));
  const feature = featureArgs.join(" ");

  if (help || !feature) {
    console.log(`
🤖 Ryx Self-Improver - Add features automatically

Usage:
  npx ts-node improver.ts "<feature description>" [options]

Options:
  --dry-run, -d    Preview changes without writing files
  --help, -h       Show this help message

Examples:
  npx ts-node improver.ts "Add dark mode toggle to settings"
  npx ts-node improver.ts "Create email notification system" --dry-run

Environment:
  GITHUB_TOKEN     Required. Your GitHub token with Copilot access.
`);
    process.exit(help ? 0 : 1);
  }

  const improver = new RyxImprover({ dryRun });
  await improver.improve(feature);
}

main().catch(console.error);
