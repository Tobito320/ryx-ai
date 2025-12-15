/**
 * Exam Evaluation Page
 * 
 * Full exam evaluation interface with file upload and streaming visualization
 */

import { useState } from 'react';
import { ExamEvaluationDashboard } from '@/components/streaming';

export default function ExamEvaluationPage() {
  const [filePath, setFilePath] = useState("");
  const [examId, setExamId] = useState("");
  const [useSandbox, setUseSandbox] = useState(false);
  const [sandboxType, setSandboxType] = useState<'docker' | 'e2b'>('docker');
  const [isConfigured, setIsConfigured] = useState(false);

  const handleStart = () => {
    if (filePath) {
      setIsConfigured(true);
    }
  };

  if (isConfigured) {
    return (
      <ExamEvaluationDashboard
        filePath={filePath}
        examId={examId}
        useSandbox={useSandbox}
        sandboxType={sandboxType}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-8">
      <div className="max-w-md w-full bg-gray-900 rounded-xl p-8 shadow-2xl">
        <h1 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
          📝 Exam Evaluation
        </h1>

        <div className="space-y-4">
          {/* File Path */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Exam File Path
            </label>
            <input
              type="text"
              value={filePath}
              onChange={(e) => setFilePath(e.target.value)}
              placeholder="/uploads/exam.pdf"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Exam ID */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Exam ID (optional)
            </label>
            <input
              type="text"
              value={examId}
              onChange={(e) => setExamId(e.target.value)}
              placeholder="exam_001"
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Sandbox Toggle */}
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">
              Use Sandbox Isolation
            </label>
            <button
              onClick={() => setUseSandbox(!useSandbox)}
              className={`relative w-12 h-6 rounded-full transition-colors ${
                useSandbox ? 'bg-blue-600' : 'bg-gray-700'
              }`}
            >
              <span
                className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  useSandbox ? 'translate-x-7' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {/* Sandbox Type */}
          {useSandbox && (
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Sandbox Type
              </label>
              <div className="flex gap-3">
                <button
                  onClick={() => setSandboxType('docker')}
                  className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                    sandboxType === 'docker'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  🐳 Docker
                </button>
                <button
                  onClick={() => setSandboxType('e2b')}
                  className={`flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors ${
                    sandboxType === 'e2b'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  ☁️ E2B Cloud
                </button>
              </div>
            </div>
          )}

          {/* Start Button */}
          <button
            onClick={handleStart}
            disabled={!filePath}
            className={`w-full py-3 rounded-lg font-semibold transition-colors ${
              filePath
                ? 'bg-green-600 hover:bg-green-500 text-white'
                : 'bg-gray-700 text-gray-500 cursor-not-allowed'
            }`}
          >
            Start Evaluation 🚀
          </button>
        </div>

        {/* Info */}
        <div className="mt-6 p-4 bg-gray-800/50 rounded-lg">
          <h3 className="text-sm font-medium text-gray-300 mb-2">
            ℹ️ What happens:
          </h3>
          <ol className="text-xs text-gray-500 space-y-1">
            <li>1. 📥 Document ingestion</li>
            <li>2. 📸 OCR & image analysis</li>
            <li>3. 📋 Rubric generation</li>
            <li>4. 🔍 Answer evaluation</li>
            <li>5. ✍️ Feedback generation</li>
            <li>6. 📊 Grade aggregation</li>
            <li>7. 📄 Report generation</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
