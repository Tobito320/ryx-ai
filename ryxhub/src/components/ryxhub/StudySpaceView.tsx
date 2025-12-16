/**
 * Study Space View Component
 * 
 * Integrates the Study Space feature into RyxHub with dark theme
 * Using RyxHub's color scheme (#1a1a1a dark, #14b8a6 teal accents)
 */

import { Suspense } from "react";
import StudySpaceLayout from "../../features/study-space/StudySpaceLayout";

export function StudySpaceView() {
  return (
    <div className="flex-1 flex flex-col h-full bg-background">
      <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground">Loading Study Spaces...</div>}>
        <StudySpaceLayout />
      </Suspense>
    </div>
  );
}
