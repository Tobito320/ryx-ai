"""
PDF Viewer - Built-in PDF viewing and form filling

Uses pdf.js for rendering PDFs in WebView.
Supports:
- PDF viewing with zoom/navigation
- Form filling
- Annotations (view)
- Print

Lazy-loaded to save memory.
"""

from pathlib import Path
from typing import Optional
import base64
import tempfile
import shutil

# Inline pdf.js viewer HTML (minimal version)
# We'll load the actual pdf.js from CDN to keep the package small
PDF_VIEWER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>PDF Viewer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            background: #1a1a1f;
            color: #ccc;
            font-family: system-ui, sans-serif;
            overflow: hidden;
        }
        
        #toolbar {
            background: #0e0e12;
            padding: 8px 16px;
            display: flex;
            align-items: center;
            gap: 12px;
            border-bottom: 1px solid #2a2a30;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 100;
        }
        
        #toolbar button {
            background: #2a2a30;
            border: none;
            color: #ccc;
            padding: 6px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        
        #toolbar button:hover {
            background: #3a3a40;
        }
        
        #page-info {
            color: #888;
            font-size: 13px;
        }
        
        #zoom-level {
            color: #888;
            font-size: 13px;
            min-width: 50px;
            text-align: center;
        }
        
        #viewer-container {
            position: fixed;
            top: 48px;
            left: 0;
            right: 0;
            bottom: 0;
            overflow: auto;
            background: #1a1a1f;
        }
        
        #viewer {
            margin: 20px auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
        }
        
        .page {
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }
        
        #loading {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #666;
            font-size: 16px;
        }
        
        /* Form field styling */
        .pdf-form-field {
            background: rgba(124, 58, 237, 0.1);
            border: 1px solid rgba(124, 58, 237, 0.3);
        }
        
        .pdf-form-field:focus {
            background: rgba(124, 58, 237, 0.2);
            border-color: #7c3aed;
            outline: none;
        }
    </style>
</head>
<body>
    <div id="toolbar">
        <button onclick="prevPage()">← Prev</button>
        <span id="page-info">Page 1 / 1</span>
        <button onclick="nextPage()">Next →</button>
        <span style="flex:1"></span>
        <button onclick="zoomOut()">−</button>
        <span id="zoom-level">100%</span>
        <button onclick="zoomIn()">+</button>
        <span style="flex:1"></span>
        <button onclick="downloadPDF()">Download</button>
        <button onclick="printPDF()">Print</button>
    </div>
    
    <div id="viewer-container">
        <div id="loading">Loading PDF...</div>
        <div id="viewer"></div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
    <script>
        pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
        
        let pdfDoc = null;
        let currentPage = 1;
        let zoom = 1.0;
        let pdfData = null;
        
        async function loadPDF(data) {
            pdfData = data;
            document.getElementById('loading').style.display = 'block';
            
            try {
                pdfDoc = await pdfjsLib.getDocument({data: atob(data)}).promise;
                document.getElementById('loading').style.display = 'none';
                updatePageInfo();
                renderAllPages();
            } catch (e) {
                document.getElementById('loading').textContent = 'Error loading PDF: ' + e.message;
            }
        }
        
        async function renderAllPages() {
            const viewer = document.getElementById('viewer');
            viewer.innerHTML = '';
            
            for (let i = 1; i <= pdfDoc.numPages; i++) {
                const page = await pdfDoc.getPage(i);
                const scale = zoom * 1.5;
                const viewport = page.getViewport({scale});
                
                const canvas = document.createElement('canvas');
                canvas.className = 'page';
                canvas.width = viewport.width;
                canvas.height = viewport.height;
                
                const ctx = canvas.getContext('2d');
                await page.render({canvasContext: ctx, viewport}).promise;
                
                viewer.appendChild(canvas);
                
                // Render form fields if present
                const annotations = await page.getAnnotations();
                renderFormFields(annotations, canvas, viewport);
            }
        }
        
        function renderFormFields(annotations, canvas, viewport) {
            annotations.forEach(ann => {
                if (ann.subtype === 'Widget') {
                    const rect = ann.rect;
                    const input = document.createElement('input');
                    input.className = 'pdf-form-field';
                    input.style.position = 'absolute';
                    input.style.left = (rect[0] * zoom * 1.5) + 'px';
                    input.style.top = (canvas.height - rect[3] * zoom * 1.5) + 'px';
                    input.style.width = ((rect[2] - rect[0]) * zoom * 1.5) + 'px';
                    input.style.height = ((rect[3] - rect[1]) * zoom * 1.5) + 'px';
                    
                    if (ann.fieldType === 'Tx') {
                        input.type = 'text';
                        input.value = ann.fieldValue || '';
                    } else if (ann.fieldType === 'Btn') {
                        input.type = 'checkbox';
                        input.checked = ann.fieldValue === 'Yes';
                    }
                    
                    canvas.parentElement.style.position = 'relative';
                    canvas.parentElement.appendChild(input);
                }
            });
        }
        
        function updatePageInfo() {
            document.getElementById('page-info').textContent = 
                `Page ${currentPage} / ${pdfDoc.numPages}`;
            document.getElementById('zoom-level').textContent = 
                Math.round(zoom * 100) + '%';
        }
        
        function prevPage() {
            if (currentPage > 1) {
                currentPage--;
                scrollToPage(currentPage);
                updatePageInfo();
            }
        }
        
        function nextPage() {
            if (currentPage < pdfDoc.numPages) {
                currentPage++;
                scrollToPage(currentPage);
                updatePageInfo();
            }
        }
        
        function scrollToPage(num) {
            const pages = document.querySelectorAll('.page');
            if (pages[num - 1]) {
                pages[num - 1].scrollIntoView({behavior: 'smooth'});
            }
        }
        
        function zoomIn() {
            zoom = Math.min(zoom + 0.25, 3.0);
            updatePageInfo();
            renderAllPages();
        }
        
        function zoomOut() {
            zoom = Math.max(zoom - 0.25, 0.5);
            updatePageInfo();
            renderAllPages();
        }
        
        function downloadPDF() {
            const blob = new Blob([Uint8Array.from(atob(pdfData), c => c.charCodeAt(0))], {type: 'application/pdf'});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'document.pdf';
            a.click();
            URL.revokeObjectURL(url);
        }
        
        function printPDF() {
            window.print();
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', e => {
            if (e.key === 'ArrowLeft') prevPage();
            else if (e.key === 'ArrowRight') nextPage();
            else if (e.key === '+' || e.key === '=') zoomIn();
            else if (e.key === '-') zoomOut();
        });
        
        // Listen for PDF data from Python
        window.loadPDFData = loadPDF;
    </script>
</body>
</html>
"""


class PDFViewer:
    """PDF viewer using pdf.js"""
    
    def __init__(self):
        self._temp_dir = None
    
    def open_pdf_url(self, webview, url: str):
        """Open PDF from URL"""
        # For URLs, we download first then display
        # This is handled by the browser's download interception
        pass
    
    def open_pdf_file(self, webview, file_path: str):
        """Open PDF from local file"""
        path = Path(file_path)
        if not path.exists():
            print(f"PDF not found: {file_path}")
            return
        
        # Read and encode PDF
        pdf_data = path.read_bytes()
        pdf_base64 = base64.b64encode(pdf_data).decode('ascii')
        
        # Load viewer HTML
        webview.load_html(PDF_VIEWER_HTML, f"file://{path.parent}/")
        
        # After load, inject PDF data
        def on_load(webview, event):
            if event == 3:  # FINISHED
                webview.evaluate_javascript(
                    f"window.loadPDFData('{pdf_base64}');",
                    -1, None, None, None, None, None
                )
                webview.disconnect_by_func(on_load)
        
        webview.connect('load-changed', on_load)
    
    def open_pdf_data(self, webview, data: bytes, filename: str = "document.pdf"):
        """Open PDF from bytes"""
        pdf_base64 = base64.b64encode(data).decode('ascii')
        
        webview.load_html(PDF_VIEWER_HTML, "about:blank")
        
        def on_load(webview, event):
            if event == 3:  # FINISHED
                webview.evaluate_javascript(
                    f"window.loadPDFData('{pdf_base64}');",
                    -1, None, None, None, None, None
                )
                webview.disconnect_by_func(on_load)
        
        webview.connect('load-changed', on_load)
    
    def cleanup(self):
        """Cleanup temporary files"""
        if self._temp_dir and Path(self._temp_dir).exists():
            shutil.rmtree(self._temp_dir)


# Lazy loading
_instance: Optional[PDFViewer] = None

def get_pdf_viewer() -> PDFViewer:
    """Get or create PDF viewer"""
    global _instance
    if _instance is None:
        _instance = PDFViewer()
    return _instance

def unload_pdf_viewer():
    """Unload PDF viewer"""
    global _instance
    if _instance:
        _instance.cleanup()
        _instance = None
