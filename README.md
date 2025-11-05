
🎯 Overview

Career Redirector is an intelligent web application built with Streamlit and OpenAI’s API, designed to instantly redirect users to the Careers / Jobs page of any company.
Just type a company name (e.g., NVIDIA, Goldman Sachs, OpenAI) — the app intelligently detects the official website and career portal using LLM reasoning, web search heuristics, and real-time URL validation.


⚙️ Tech Stack

Frontend: Streamlit

Backend Intelligence: OpenAI GPT-4 API

HTTP Client: HTTPX

Parsing: BeautifulSoup4

Environment Management: python-dotenv

💡 Key Features

✅ Smart company name normalization and URL guessing
✅ Multi-tier OpenAI fallback logic (compatible with any SDK version)
✅ DuckDuckGo-based web search fallback
✅ Automatic or manual redirect to verified Careers pages
✅ Clean Streamlit UI with toggle options (debug, redirect, link mode)
✅ Deployed and optimized for Mac/PyCharm local setup

🧰 Setup Instructions
# 1. Clone this repository
git clone https://github.com/bhavesh-kalluru/career-redirector.git
cd career-redirector

# 2. Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # (Mac/Linux)
venv\Scripts\activate     # (Windows)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your OpenAI key
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 5. Run the app
streamlit run app.py

🧠 How It Works

The user inputs a company name or URL.

The system normalizes input → checks popular company domains.

If unknown, OpenAI analyzes and returns structured JSON (company, official_website, careers_url).

If still unresolved, it falls back to web heuristics and DuckDuckGo search.

Finally, Streamlit displays both official and career links (with optional auto-redirect).

🧩 Example Usage
Input	Output Careers URL
OpenAI	https://openai.com/careers

Google	https://careers.google.com

Nvidia	https://www.nvidia.com/en-us/about-nvidia/careers/
🌎 Future Enhancements

Deploy on Streamlit Cloud / AWS

Add LinkedIn Jobs and Indeed integrations

Multi-model fallback (Anthropic / Gemini)

Personalized role search based on user profile

👨‍💻 Author

Bhavesh Kalluru
🎓 Passionate about AI, data-driven applications, and full-stack innovation.
📍 Currently seeking full-time opportunities in the United States (AI/ML, Software, or Data roles).

📧 kallurubhavesh341@gmail.com
🔗 https://www.linkedin.com/in/bhaveshkalluru/ | kbhavesh.com

⭐ Show Your Support

If you find this helpful, star the repo and share it with your network!
Contributions and feedback are welcome. 🙌
