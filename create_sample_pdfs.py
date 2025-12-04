#!/usr/bin/env python3
"""
Create sample PDF files for the preloaded documents folder
"""

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    import os
    
    def create_sample_pdfs():
        preloaded_folder = "preloaded_pdfs"
        os.makedirs(preloaded_folder, exist_ok=True)
        
        # Sample PDF 1: Technology Guide
        filename1 = os.path.join(preloaded_folder, "technology_guide.pdf")
        c1 = canvas.Canvas(filename1, pagesize=letter)
        
        c1.drawString(100, 750, "Technology Guide 2025")
        c1.drawString(100, 720, "A Comprehensive Overview of Modern Technology")
        c1.drawString(100, 690, "")
        c1.drawString(100, 660, "Chapter 1: Artificial Intelligence")
        c1.drawString(100, 630, "Artificial Intelligence (AI) is revolutionizing how we work and live.")
        c1.drawString(100, 600, "Machine learning algorithms can process vast amounts of data")
        c1.drawString(100, 570, "to identify patterns and make predictions.")
        c1.drawString(100, 540, "")
        c1.drawString(100, 510, "Chapter 2: Cloud Computing")
        c1.drawString(100, 480, "Cloud computing provides scalable and flexible computing resources")
        c1.drawString(100, 450, "over the internet. It enables businesses to reduce costs")
        c1.drawString(100, 420, "and improve efficiency through on-demand resource allocation.")
        c1.drawString(100, 390, "")
        c1.drawString(100, 360, "Chapter 3: Cybersecurity")
        c1.drawString(100, 330, "As technology advances, cybersecurity becomes increasingly important.")
        c1.drawString(100, 300, "Organizations must implement robust security measures")
        c1.drawString(100, 270, "to protect sensitive data and maintain user trust.")
        
        c1.save()
        
        # Sample PDF 2: Business Strategy
        filename2 = os.path.join(preloaded_folder, "business_strategy.pdf")
        c2 = canvas.Canvas(filename2, pagesize=letter)
        
        c2.drawString(100, 750, "Modern Business Strategy")
        c2.drawString(100, 720, "Strategic Planning for the Digital Age")
        c2.drawString(100, 690, "")
        c2.drawString(100, 660, "Executive Summary")
        c2.drawString(100, 630, "This document outlines key strategies for modern businesses")
        c2.drawString(100, 600, "to thrive in the digital economy.")
        c2.drawString(100, 570, "")
        c2.drawString(100, 540, "Digital Transformation")
        c2.drawString(100, 510, "Companies must embrace digital transformation to remain competitive.")
        c2.drawString(100, 480, "This includes adopting new technologies, improving processes,")
        c2.drawString(100, 450, "and enhancing customer experiences.")
        c2.drawString(100, 420, "")
        c2.drawString(100, 390, "Customer-Centric Approach")
        c2.drawString(100, 360, "Successful businesses prioritize customer needs and preferences.")
        c2.drawString(100, 330, "Understanding customer behavior through data analytics")
        c2.drawString(100, 300, "enables personalized experiences and improved satisfaction.")
        c2.drawString(100, 270, "")
        c2.drawString(100, 240, "Innovation and Agility")
        c2.drawString(100, 210, "Organizations must foster innovation and maintain agility")
        c2.drawString(100, 180, "to adapt quickly to market changes and opportunities.")
        
        c2.save()
        
        # Sample PDF 3: Health and Wellness
        filename3 = os.path.join(preloaded_folder, "health_wellness.pdf")
        c3 = canvas.Canvas(filename3, pagesize=letter)
        
        c3.drawString(100, 750, "Health and Wellness Guide")
        c3.drawString(100, 720, "A Complete Guide to Healthy Living")
        c3.drawString(100, 690, "")
        c3.drawString(100, 660, "Introduction")
        c3.drawString(100, 630, "Maintaining good health requires a holistic approach")
        c3.drawString(100, 600, "that includes proper nutrition, regular exercise,")
        c3.drawString(100, 570, "adequate sleep, and stress management.")
        c3.drawString(100, 540, "")
        c3.drawString(100, 510, "Nutrition Guidelines")
        c3.drawString(100, 480, "A balanced diet should include fruits, vegetables, whole grains,")
        c3.drawString(100, 450, "lean proteins, and healthy fats. Limiting processed foods")
        c3.drawString(100, 420, "and added sugars is essential for optimal health.")
        c3.drawString(100, 390, "")
        c3.drawString(100, 360, "Exercise Recommendations")
        c3.drawString(100, 330, "Adults should engage in at least 150 minutes of moderate-intensity")
        c3.drawString(100, 300, "aerobic activity per week, plus muscle-strengthening activities")
        c3.drawString(100, 270, "on two or more days per week.")
        c3.drawString(100, 240, "")
        c3.drawString(100, 210, "Mental Health")
        c3.drawString(100, 180, "Mental health is equally important as physical health.")
        c3.drawString(100, 150, "Practice stress management techniques and seek support when needed.")
        
        c3.save()
        
        print(f"Created sample PDFs in {preloaded_folder}:")
        print(f"- {filename1}")
        print(f"- {filename2}")
        print(f"- {filename3}")
        
        return [filename1, filename2, filename3]
    
    if __name__ == "__main__":
        create_sample_pdfs()
        
except ImportError:
    print("reportlab not available. Please install it: pip install reportlab")
    print("Or manually add PDF files to the backend/preloaded_pdfs/ folder")