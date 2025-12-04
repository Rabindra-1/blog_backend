# Knowledge Base PDFs

This folder contains PDF documents that are automatically loaded into the AI chat system.

## How to Add PDFs:
1. Place PDF files in this folder
2. Restart the Django server
3. PDFs will be automatically processed and available for chat

## Current PDFs:
- sample_blog_writing.pdf - Guide on blog writing techniques
- content_creation.pdf - Content creation best practices
- seo_guide.pdf - SEO optimization guide

## Supported Formats:
- PDF files only
- Maximum file size: 50MB per file
- Text-based PDFs (scanned PDFs may not work well)

## Processing:
- PDFs are processed on server startup
- Text is extracted and indexed for fast search
- Users can ask questions and get blog-style responses