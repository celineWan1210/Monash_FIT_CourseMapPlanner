# Monash FIT Course Map Planner

A tool for Monash FIT students that helps plan courses with AI analysis. The AI advisor recommends optimal paths based on your course selections, while the system automatically fetches course information and visualizes your planned course load.

---

## Features
- **AI course plan analysis** using Gemini API  
- **Web scraping** for up-to-date course information  
- **Interactive web interface** using Flask  
- **Visualizations** of course load per semester  
- **Flexible course planning** with core/elective swapping  
- **Smart elective recommendations** using machine learning (TF-IDF + cosine similarity)  

---

## Setup Instructions

### 1. Download the code
Clone or download this repository.

### 2. Install Chrome Driver
Download Chrome driver from [here](https://googlechromelabs.github.io/chrome-for-testing/#stable) and update the path in `scrape.py` (line 17).

### 3. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

#Install library
pip install flask flask-cors scikit-learn matplotlib beautifulsoup4 selenium google-generativeai nltk
```
### 4. Run the website
python3 app.py

