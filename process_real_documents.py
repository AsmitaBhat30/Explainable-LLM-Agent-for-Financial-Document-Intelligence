"""
Document Processors for Real Financial Documents
Handles SEC filings (HTML), EU regulations (HTML), and PDFs
"""

import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import PyPDF2
from dataclasses import dataclass
import json


@dataclass
class ProcessedDocument:
    """Standardized document structure."""
    doc_id: str
    doc_type: str
    source: str
    title: str
    text: str
    sections: List[Dict]
    tables: List[Dict]
    metadata: Dict
    file_hash: str


class SECFilingProcessor:
    """Process SEC EDGAR HTML filings (10-K, 10-Q)."""
    
    def __init__(self):
        self.section_patterns = {
            'item_1': r'Item\s+1[.\s]+Business',
            'item_1a': r'Item\s+1A[.\s]+Risk Factors',
            'item_2': r'Item\s+2[.\s]+Properties',
            'item_3': r'Item\s+3[.\s]+Legal Proceedings',
            'item_7': r'Item\s+7[.\s]+Management.*Discussion',
            'item_8': r'Item\s+8[.\s]+Financial Statements',
            'item_9a': r'Item\s+9A[.\s]+Controls and Procedures'
        }
    
    def process(self, filepath: Path) -> ProcessedDocument:
        """Process SEC HTML filing."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for element in soup(['script', 'style', 'meta', 'link']):
            element.decompose()
        
        # Extract title
        title = self._extract_title(soup)
        
        # Extract sections
        sections = self._extract_sections(soup, html_content)
        
        # Extract tables
        tables = self._extract_tables(soup)
        
        # Full text
        text = soup.get_text(separator='\n', strip=True)
        
        # Clean text
        text = self._clean_text(text)
        
        # Generate document ID
        file_hash = hashlib.sha256(text.encode()).hexdigest()
        doc_id = f"sec_{file_hash[:12]}"
        
        # Extract metadata
        metadata = self._extract_sec_metadata(filepath, soup, title)
        
        return ProcessedDocument(
            doc_id=doc_id,
            doc_type="annual_report",
            source="SEC Edgar",
            title=title,
            text=text,
            sections=sections,
            tables=tables,
            metadata=metadata,
            file_hash=file_hash
        )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract document title."""
        # Try multiple methods
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # Look for h1 or prominent text
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        return "SEC Filing"
    
    def _extract_sections(self, soup: BeautifulSoup, html_content: str) -> List[Dict]:
        """Extract 10-K sections (Items)."""
        sections = []
        
        for section_key, pattern in self.section_patterns.items():
            matches = re.finditer(pattern, html_content, re.IGNORECASE)
            
            for match in matches:
                start_pos = match.start()
                # Find the next section or end
                section_text = html_content[start_pos:start_pos + 50000]  # Max 50k chars per section
                
                # Clean HTML
                section_soup = BeautifulSoup(section_text, 'html.parser')
                clean_text = section_soup.get_text(separator='\n', strip=True)
                
                if len(clean_text) > 100:  # Valid section
                    sections.append({
                        'section_id': section_key,
                        'section_name': match.group(0),
                        'text': clean_text[:10000],  # First 10k chars
                        'start_position': start_pos
                    })
        
        return sections
    
    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract financial tables."""
        tables = []
        
        for idx, table in enumerate(soup.find_all('table')[:20]):  # Limit to first 20 tables
            rows = []
            
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append(cells)
            
            if len(rows) > 1:  # Valid table
                tables.append({
                    'table_id': f"table_{idx}",
                    'rows': rows[:50],  # Limit rows
                    'row_count': len(rows),
                    'col_count': len(rows[0]) if rows else 0
                })
        
        return tables
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        # Remove page numbers
        text = re.sub(r'^\s*\d+\s*$', '', text, flags=re.MULTILINE)
        # Remove excessive spaces
        text = re.sub(r' +', ' ', text)
        return text.strip()
    
    def _extract_sec_metadata(self, filepath: Path, soup: BeautifulSoup, title: str) -> Dict:
        """Extract SEC-specific metadata."""
        filename = filepath.stem
        
        # Parse company and year from filename
        company = "Unknown"
        year = None
        
        if 'jpmorgan' in filename.lower():
            company = "JPMorgan Chase & Co."
        elif 'bofa' in filename.lower():
            company = "Bank of America Corporation"
        elif 'goldman' in filename.lower():
            company = "Goldman Sachs Group, Inc."
        elif 'jefferies' in filename.lower():
            company = "Jefferies Financial Group Inc."
        
        # Extract year
        year_match = re.search(r'20\d{2}', filename)
        if year_match:
            year = int(year_match.group())
        
        return {
            'company': company,
            'fiscal_year': year,
            'filing_type': '10-K',
            'source_file': filename,
            'processing_date': datetime.now().isoformat(),
            'text_length': len(title),
            'language': 'en'
        }


class EURegulationProcessor:
    """Process EUR-Lex regulation HTML documents."""
    
    def process(self, filepath: Path) -> ProcessedDocument:
        """Process EU regulation HTML."""
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove navigation and scripts
        for element in soup(['script', 'style', 'nav', 'header', 'footer']):
            element.decompose()
        
        # Extract title
        title = self._extract_title(soup, filepath)
        
        # Extract articles/sections
        sections = self._extract_articles(soup)
        
        # Full text
        text = soup.get_text(separator='\n', strip=True)
        text = self._clean_text(text)
        
        # Generate document ID
        file_hash = hashlib.sha256(text.encode()).hexdigest()
        doc_id = f"eur_{file_hash[:12]}"
        
        # Extract metadata
        metadata = self._extract_regulation_metadata(filepath, title)
        
        return ProcessedDocument(
            doc_id=doc_id,
            doc_type="regulation",
            source="EUR-Lex",
            title=title,
            text=text,
            sections=sections,
            tables=[],
            metadata=metadata,
            file_hash=file_hash
        )
    
    def _extract_title(self, soup: BeautifulSoup, filepath: Path) -> str:
        """Extract regulation title."""
        # Try h1 or title
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)
        
        # Fallback to filename
        filename = filepath.stem
        if 'mifid' in filename.lower():
            return "Markets in Financial Instruments Directive (MiFID II)"
        elif 'psd2' in filename.lower():
            return "Payment Services Directive 2 (PSD2)"
        elif 'gdpr' in filename.lower():
            return "General Data Protection Regulation (GDPR)"
        elif 'crr' in filename.lower():
            return "Capital Requirements Regulation (CRR)"
        
        return "EU Regulation"
    
    def _extract_articles(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract regulation articles."""
        sections = []
        
        # Look for article tags or headings
        article_pattern = r'Article\s+(\d+)'
        
        # Find all potential article headers
        for idx, heading in enumerate(soup.find_all(['h2', 'h3', 'h4', 'p', 'div'])):
            text = heading.get_text(strip=True)
            match = re.match(article_pattern, text, re.IGNORECASE)
            
            if match:
                article_num = match.group(1)
                
                # Get following content
                content = []
                for sibling in heading.find_next_siblings():
                    if sibling.name in ['h2', 'h3'] and re.match(article_pattern, sibling.get_text()):
                        break
                    content.append(sibling.get_text(strip=True))
                
                article_text = '\n'.join(content)
                
                if len(article_text) > 50:
                    sections.append({
                        'section_id': f"article_{article_num}",
                        'section_name': text,
                        'text': article_text[:5000],
                        'article_number': int(article_num)
                    })
        
        return sections[:100]  # Limit sections
    
    def _clean_text(self, text: str) -> str:
        """Clean regulation text."""
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
    
    def _extract_regulation_metadata(self, filepath: Path, title: str) -> Dict:
        """Extract regulation metadata."""
        filename = filepath.stem
        
        regulation_type = "Unknown"
        if 'mifid' in filename.lower():
            regulation_type = "MiFID II"
        elif 'psd2' in filename.lower():
            regulation_type = "PSD2"
        elif 'gdpr' in filename.lower():
            regulation_type = "GDPR"
        elif 'crr' in filename.lower():
            regulation_type = "CRR"
        
        return {
            'regulation_type': regulation_type,
            'jurisdiction': 'EU',
            'source_file': filename,
            'processing_date': datetime.now().isoformat(),
            'language': 'en'
        }


class PDFProcessor:
    """Process PDF documents (BaFin, Basel, ECB)."""
    
    def process(self, filepath: Path) -> ProcessedDocument:
        """Process PDF document."""
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # Extract text from all pages
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            
            page_count = len(reader.pages)
        
        # Clean text
        text = self._clean_text(text)
        
        # Extract sections (basic)
        sections = self._extract_sections(text)
        
        # Generate document ID
        file_hash = hashlib.sha256(text.encode()).hexdigest()
        doc_id = f"pdf_{file_hash[:12]}"
        
        # Determine source and type
        source, doc_type, title = self._identify_document(filepath, text)
        
        # Metadata
        metadata = {
            'source_file': filepath.name,
            'page_count': page_count,
            'processing_date': datetime.now().isoformat(),
            'text_length': len(text),
            'language': 'en'
        }
        
        return ProcessedDocument(
            doc_id=doc_id,
            doc_type=doc_type,
            source=source,
            title=title,
            text=text,
            sections=sections,
            tables=[],
            metadata=metadata,
            file_hash=file_hash
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean PDF text."""
        # Remove page breaks
        text = re.sub(r'\f', '\n', text)
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        return text.strip()
    
    def _extract_sections(self, text: str) -> List[Dict]:
        """Extract sections from PDF (basic heading detection)."""
        sections = []
        
        # Simple section detection by numbered headings
        section_pattern = r'^(\d+\.?\d*)\s+([A-Z][A-Za-z\s]{3,50}?)$'
        
        lines = text.split('\n')
        current_section = None
        current_text = []
        
        for line in lines:
            match = re.match(section_pattern, line.strip())
            
            if match:
                # Save previous section
                if current_section and current_text:
                    sections.append({
                        'section_id': f"section_{current_section}",
                        'section_name': current_section,
                        'text': '\n'.join(current_text)[:5000]
                    })
                
                current_section = line.strip()
                current_text = []
            else:
                current_text.append(line)
        
        # Add final section
        if current_section and current_text:
            sections.append({
                'section_id': f"section_{len(sections)}",
                'section_name': current_section,
                'text': '\n'.join(current_text)[:5000]
            })
        
        return sections[:50]
    
    def _identify_document(self, filepath: Path, text: str) -> tuple:
        """Identify document source and type."""
        filename = filepath.stem.lower()
        text_lower = text.lower()
        
        # BaFin documents
        if 'bafin' in filename:
            if 'annual' in filename:
                return "BaFin", "annual_report", "BaFin Annual Report"
            else:
                return "BaFin", "guidance", "BaFin Guidance Notice"
        
        # Basel documents
        if 'basel' in filename or 'bcbs' in filename:
            return "BIS Basel Committee", "regulation", "Basel Committee Document"
        
        # ECB documents
        if 'ecb' in filename or 'supervisory' in filename:
            return "European Central Bank", "guidance", "ECB Supervisory Document"
        
        return "Unknown", "document", "Financial Document"


class DocumentProcessorOrchestrator:
    """Orchestrate processing of all document types."""
    
    def __init__(self, raw_dir: str = "data/raw", parsed_dir: str = "data/parsed"):
        self.raw_dir = Path(raw_dir)
        self.parsed_dir = Path(parsed_dir)
        self.parsed_dir.mkdir(parents=True, exist_ok=True)
        
        self.sec_processor = SECFilingProcessor()
        self.eu_processor = EURegulationProcessor()
        self.pdf_processor = PDFProcessor()
    
    def process_all(self) -> List[ProcessedDocument]:
        """Process all documents in raw directory."""
        documents = []
        
        for filepath in self.raw_dir.glob('*'):
            if filepath.is_dir() or filepath.name.startswith('.'):
                continue
            
            try:
                print(f"\nProcessing: {filepath.name}")
                
                # Route to appropriate processor
                if filepath.suffix == '.html':
                    if 'jpm' in filepath.name.lower() or 'bofa' in filepath.name.lower() or \
                       'goldman' in filepath.name.lower() or 'jefferies' in filepath.name.lower():
                        doc = self.sec_processor.process(filepath)
                    else:
                        doc = self.eu_processor.process(filepath)
                
                elif filepath.suffix == '.pdf':
                    doc = self.pdf_processor.process(filepath)
                
                else:
                    print(f"  ⚠ Unsupported format: {filepath.suffix}")
                    continue
                
                # Save processed document
                self._save_processed(doc)
                documents.append(doc)
                
                print(f"  ✓ Processed: {doc.title[:60]}...")
                print(f"    - Sections: {len(doc.sections)}")
                print(f"    - Tables: {len(doc.tables)}")
                print(f"    - Text length: {len(doc.text):,} chars")
            
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
        
        return documents
    
    def _save_processed(self, doc: ProcessedDocument):
        """Save processed document to JSON."""
        output_file = self.parsed_dir / f"{doc.doc_id}.json"
        
        doc_dict = {
            'doc_id': doc.doc_id,
            'doc_type': doc.doc_type,
            'source': doc.source,
            'title': doc.title,
            'text': doc.text,
            'sections': doc.sections,
            'tables': doc.tables,
            'metadata': doc.metadata,
            'file_hash': doc.file_hash
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(doc_dict, f, indent=2, ensure_ascii=False)


def main():
    """Main execution."""
    print("="*60)
    print("DOCUMENT PROCESSING PIPELINE")
    print("="*60)
    
    orchestrator = DocumentProcessorOrchestrator()
    documents = orchestrator.process_all()
    
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print(f"\nTotal documents processed: {len(documents)}")
    print(f"Saved to: {orchestrator.parsed_dir}")
    
    # Summary by type
    by_type = {}
    by_source = {}
    
    for doc in documents:
        by_type[doc.doc_type] = by_type.get(doc.doc_type, 0) + 1
        by_source[doc.source] = by_source.get(doc.source, 0) + 1
    
    print("\nBy document type:")
    for doc_type, count in by_type.items():
        print(f"  - {doc_type}: {count}")
    
    print("\nBy source:")
    for source, count in by_source.items():
        print(f"  - {source}: {count}")


if __name__ == "__main__":
    main()