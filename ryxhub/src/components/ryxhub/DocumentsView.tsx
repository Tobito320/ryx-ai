import { useState, useEffect } from "react";
import { FileText, Upload, Folder, Search, Trash2, Eye, Download, Plus, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface Document {
  id: string;
  name: string;
  type: string;
  size: number;
  uploadedAt: string;
  indexed: boolean;
  folder?: string;
}

interface Folder {
  id: string;
  name: string;
  documentCount: number;
}

export function DocumentsView() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [dragActive, setDragActive] = useState(false);

  // Load documents from API
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:8420/api/rag/documents');
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents || []);
        setFolders(data.folders || []);
      }
    } catch (error) {
      console.warn('Failed to load documents:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUpload = async (files: FileList | File[]) => {
    setIsUploading(true);
    const fileArray = Array.from(files);
    
    try {
      for (const file of fileArray) {
        const formData = new FormData();
        formData.append('file', file);
        if (selectedFolder) {
          formData.append('folder', selectedFolder);
        }

        const response = await fetch('http://localhost:8420/api/rag/upload', {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          toast.success(`Uploaded: ${file.name}`);
        } else {
          toast.error(`Failed to upload: ${file.name}`);
        }
      }
      await loadDocuments();
    } catch (error) {
      toast.error('Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string, docName: string) => {
    if (!confirm(`Delete "${docName}"?`)) return;
    
    try {
      const response = await fetch(`http://localhost:8420/api/rag/documents/${docId}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setDocuments(prev => prev.filter(d => d.id !== docId));
        toast.success('Document deleted');
      }
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files.length > 0) {
      handleUpload(e.dataTransfer.files);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = !searchQuery || 
      doc.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFolder = !selectedFolder || doc.folder === selectedFolder;
    return matchesSearch && matchesFolder;
  });

  if (isLoading) {
    return (
      <div className="flex flex-col h-full bg-background items-center justify-center">
        <Loader2 className="w-6 h-6 animate-spin text-primary mb-2" />
        <p className="text-sm text-muted-foreground">Loading documents...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border bg-card/50 shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            <span className="text-sm font-medium">Documents</span>
            <span className="text-xs text-muted-foreground">({documents.length})</span>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs"
              onClick={() => document.getElementById('file-upload')?.click()}
              disabled={isUploading}
            >
              {isUploading ? (
                <Loader2 className="w-3 h-3 mr-1 animate-spin" />
              ) : (
                <Upload className="w-3 h-3 mr-1" />
              )}
              Upload
            </Button>
            <input
              id="file-upload"
              type="file"
              multiple
              className="hidden"
              accept=".pdf,.txt,.md,.docx,.csv,.json"
              onChange={(e) => e.target.files && handleUpload(e.target.files)}
            />
          </div>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 pl-8 text-xs"
          />
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Folders Sidebar */}
        <div className="w-48 border-r border-border p-2 shrink-0">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium mb-2 px-2">
            Folders
          </div>
          
          <button
            onClick={() => setSelectedFolder(null)}
            className={cn(
              "w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors",
              !selectedFolder ? "bg-primary/10 text-primary" : "hover:bg-muted text-muted-foreground"
            )}
          >
            <Folder className="w-3.5 h-3.5" />
            All Documents
          </button>
          
          {folders.map(folder => (
            <button
              key={folder.id}
              onClick={() => setSelectedFolder(folder.id)}
              className={cn(
                "w-full flex items-center gap-2 px-2 py-1.5 rounded text-xs transition-colors",
                selectedFolder === folder.id ? "bg-primary/10 text-primary" : "hover:bg-muted text-muted-foreground"
              )}
            >
              <Folder className="w-3.5 h-3.5" />
              <span className="flex-1 text-left truncate">{folder.name}</span>
              <span className="text-[10px] opacity-60">{folder.documentCount}</span>
            </button>
          ))}
        </div>

        {/* Documents Grid */}
        <div 
          className={cn(
            "flex-1 p-4 overflow-auto transition-colors",
            dragActive && "bg-primary/5 border-2 border-dashed border-primary/30"
          )}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          {filteredDocuments.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <FileText className="w-10 h-10 text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">No documents yet</p>
              <p className="text-xs text-muted-foreground/60 mt-1">
                Drag & drop files here or click Upload
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {filteredDocuments.map(doc => (
                <div
                  key={doc.id}
                  className="group bg-card border border-border rounded-lg p-3 hover:border-primary/30 transition-colors"
                >
                  <div className="flex items-start gap-2">
                    <FileText className="w-8 h-8 text-primary/60 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate" title={doc.name}>
                        {doc.name}
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground mt-1">
                        <span>{formatSize(doc.size)}</span>
                        <span>•</span>
                        <span className={cn(
                          "px-1 py-0.5 rounded",
                          doc.indexed ? "bg-green-500/20 text-green-600" : "bg-yellow-500/20 text-yellow-600"
                        )}>
                          {doc.indexed ? "Indexed" : "Pending"}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Actions - visible on hover */}
                  <div className="flex items-center gap-1 mt-2 pt-2 border-t border-border/50 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button variant="ghost" size="icon" className="h-6 w-6" title="Preview">
                      <Eye className="w-3 h-3" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-6 w-6" title="Download">
                      <Download className="w-3 h-3" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      className="h-6 w-6 text-destructive hover:text-destructive" 
                      title="Delete"
                      onClick={() => handleDelete(doc.id, doc.name)}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
