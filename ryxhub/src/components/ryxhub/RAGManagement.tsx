import { useState } from "react";
import { Upload, Search, Trash2, FileText, Database, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useRyxHub } from "@/context/RyxHubContext";

interface RAGDocument {
  id: string;
  name: string;
  size: number;
  uploadedAt: string;
  chunks: number;
}

interface SearchResult {
  content: string;
  score: number;
  source: string;
}

export function RAGManagement() {
  const { ragStatus } = useRyxHub();
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
      }

      const response = await fetch('http://localhost:8420/api/rag/upload', {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        toast.success(`Uploaded ${files.length} file(s)`);
        // Reset file input
        event.target.value = '';
      } else {
        toast.error('Failed to upload files');
      }
    } catch (error) {
      toast.error('Failed to upload files');
      console.error(error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const response = await fetch('http://localhost:8420/api/rag/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          top_k: 5,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setSearchResults(data.results || []);
        if (data.results.length === 0) {
          toast.info('No results found');
        }
      } else {
        toast.error('Search failed');
      }
    } catch (error) {
      toast.error('Search failed');
      console.error(error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const response = await fetch('http://localhost:8420/api/rag/sync', {
        method: 'POST',
      });

      if (response.ok) {
        const data = await response.json();
        toast.success(`Queued ${data.queued_files || 0} files for indexing`);
      } else {
        toast.error('Failed to trigger sync');
      }
    } catch (error) {
      toast.error('Failed to trigger sync');
      console.error(error);
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* RAG Status Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            RAG Index Status
          </CardTitle>
          <CardDescription>
            Knowledge base statistics and management
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Indexed Documents</p>
              <p className="text-2xl font-bold">{ragStatus.indexed.toLocaleString()}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Pending</p>
              <p className="text-2xl font-bold">{ragStatus.pending}</p>
            </div>
            <div className="space-y-1">
              <p className="text-sm text-muted-foreground">Status</p>
              <Badge variant={ragStatus.status === "idle" ? "secondary" : "default"}>
                {ragStatus.status}
              </Badge>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <AlertCircle className="w-4 h-4" />
            Last sync: {ragStatus.lastSync}
          </div>
          <Button 
            onClick={handleSync} 
            disabled={isSyncing}
            className="w-full"
          >
            {isSyncing ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Syncing...
              </>
            ) : (
              <>
                <Database className="mr-2 h-4 w-4" />
                Trigger Re-index
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Document Upload Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload Documents
          </CardTitle>
          <CardDescription>
            Add documents to the knowledge base
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
              <Upload className="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
              <p className="text-sm text-muted-foreground mb-4">
                Drag and drop files here, or click to browse
              </p>
              <Input
                type="file"
                multiple
                onChange={handleFileUpload}
                disabled={isUploading}
                className="hidden"
                id="file-upload"
                accept=".txt,.md,.pdf,.doc,.docx"
              />
              <Button 
                onClick={() => document.getElementById('file-upload')?.click()}
                disabled={isUploading}
              >
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <FileText className="mr-2 h-4 w-4" />
                    Select Files
                  </>
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Supported formats: TXT, MD, PDF, DOC, DOCX
            </p>
          </div>
        </CardContent>
      </Card>

      {/* RAG Search Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="w-5 h-5" />
            Search Knowledge Base
          </CardTitle>
          <CardDescription>
            Test RAG search with similarity scoring
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="Search for documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button 
                onClick={handleSearch} 
                disabled={isSearching || !searchQuery.trim()}
              >
                {isSearching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
              </Button>
            </div>

            {searchResults.length > 0 && (
              <ScrollArea className="h-[300px] rounded-md border p-4">
                <div className="space-y-4">
                  {searchResults.map((result, index) => (
                    <div key={index} className="space-y-2 pb-4 border-b last:border-0">
                      <div className="flex items-center justify-between">
                        <Badge variant="outline">{result.source}</Badge>
                        <span className="text-xs text-muted-foreground">
                          Score: {(result.score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-sm text-foreground">{result.content}</p>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
