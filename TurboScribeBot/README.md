# TurboScribeBot – Automated Web Scraping & File Processing Bot (Selenium, Python)

---

## 📄 Project Description

**TurboScribeBot** is a fully automated system for transcription, translation, and summarization of audio/video content. Designed for efficiency and minimal manual intervention, it streamlines the workflow for individuals and businesses who need reliable transcription services.

**Problem Solved:**
Manually transcribing audio/video content is time-consuming, error-prone, and tedious, especially when handling multiple sources such as Zoom recordings, OneDrive files, or YouTube videos.

**High-Level Solution:**
TurboScribeBot automates the entire workflow using Python, Selenium, and AI-powered text processing:

* Logs into TurboScribe.ai automatically
* Uploads files or fetches them from Zoom/OneDrive links
* Triggers transcription and monitors progress
* Post-processes transcripts: translation, summarization, timestamping, and speaker diarization

**Unique Value Proposition:**

* Fully Dockerized for easy deployment
* CLI-based for seamless integration in pipelines
* Handles multiple sources and languages
* Reliable and hands-free automation for large-scale transcription needs

---

## 🧰 Technologies & Tools Used

* **Languages & Frameworks:** Python, Selenium WebDriver
* **Automation & Testing:** ChromeDriver, Explicit Waits, Smart Selectors
* **Containerization:** Docker, Docker Compose
* **Integrations:** Zoom, OneDrive
* **AI Processing:** Translation, Summarization (short & long modes)
* **Interface:** CLI commands with argument parsing
* **Development Tools:** VS Code, Chrome DevTools
* **Version Control & Deployment:** Git, GitHub

---

## 💡 Key Achievements / Highlights

* Built a fully automated end-to-end transcription workflow
* Integrated AI features: translation and text summarization
* Supported direct transcription from Zoom and OneDrive links
* Packaged in Docker for one-command setup and portability
* Designed a flexible CLI interface for scripts and server use
* Ensured reliability with explicit waits, error handling, and robust element tracking

---

## 🧠 Skills Demonstrated

* Python Scripting & Automation
* Selenium Web Scraping & WebDriver Automation
* CLI Design & Argument Parsing
* Dockerization & Environment Setup
* API Integration (Zoom, OneDrive, AI Services)
* Text Processing (Translation & Summarization)
* Workflow Optimization & Automation
* Debugging & Error Recovery Strategies
* Clean Code Practices & Modular Architecture
* Client-Focused Problem Solving

---

## ⚙️ Installation & Setup

### 1️⃣ Build the Docker Container

```bash
docker build -t abdlrhman00/turboscribe-bot-2:v4.0 .
```

### 2️⃣ Pull from DockerHub (Private Repo)

```bash
docker pull abdlrhman00/turboscribe-bot-2:v4.0
```

### 3️⃣ Environment File (.env)

Create a `.env` file to store credentials securely:

```env
EMAIL=your_email@example.com
PASSWORD=your_password
```
---

## 📂 Outputs / Results

All results are stored under `{output}/{id}/`. Example structure:

```
outputs/51/
├── report_51.json
├── 51.log
├── transcript.txt
├── summary_detailed.txt
├── translate.txt
├── file.mp3
```

---

## 📝 Usage Guide

### Required Arguments

* `--id ID` → Unique job ID (used for folder naming)
* `--output PATH` → Path inside container for storing outputs (usually same as host path)

**Source Workflow (Zoom / OneDrive)**

* `--source [zoom|onedrive]` → Select the source workflow
* `--link URL` → Video/audio link (Zoom/OneDrive/YouTube)
* `--passcode CODE` → Required Zoom passcode if any
* `--with-transcription` → Automatically transcribe downloaded content

**Direct Transcription Workflow** *(only if `--source` is not specified)*

* `--link URL` → YouTube/video/audio link
* `--file PATH` → Local file path mounted to `/app/input_files` inside container

---

### Options

* `--language LANG` → Language for transcription (e.g., `en`, `ar`)
* `--model [base|small|large-v2]` → Model size for transcription (default: base)

---

### Features (Flags)

* `--speakers [N]` → Speaker diarization (`true`, `-1` for auto, or number of speakers)
* `--transcribe` → Transcribe original audio directly to English
* `--restore` → Enhance / restore audio quality
* `--timestamps` → Add timestamps to transcript
* `--short_summary` → Generate short GPT summary
* `--detail_summary` → Generate detailed GPT summary
* `--translate LANG` → Translate transcript (e.g., `en`, `ar`)
* `--download_audio` → Download original audio file

---

### Example Commands (CLI Style)

**Transcribe a YouTube Link**

```bash
docker run -d --rm \
  -v /hamada/TurboScribeBot:/app \
  abdlrhman00/turboscribe-bot-2:v4.0 \
  --id 600 \
  --output /hamada/TurboScribeBot/outputs/600 \
  --link 'https://youtu.be/weaGPNlSMBE?si=im23gF5TOEG1U6ag' \
  --language ar
```

**Transcribe a Local File**

```bash
docker run -d --rm \
  -v /hamada/TurboScribeBot:/app \
  -v /path/to/audio:/app/input_files:ro \
  abdlrhman00/turboscribe-bot-2:v4.0 \
  --id 52 \
  --output /hamada/TurboScribeBot/outputs/52 \
  --file /app/input_files/interview.mp3 \
  --language ar
```

**Zoom Recording + Transcription + Detailed Summary**

```bash
docker run -d --rm \
  -v /hamada/TurboScribeBot:/app \
  abdlrhman00/turboscribe-bot-2:v4.0 \
  --id 201 \
  --output /hamada/TurboScribeBot/outputs/201 \
  --source zoom \
  --link 'https://us06web.zoom.us/rec/share/abc123' \
  --passcode 'S$hB4cz#' \
  --with-transcription \
  --language ar \
  --detail_summary
```

**OneDrive Recording + Transcription + Translation**

```bash
docker run -d --rm \
  -v /hamada/TurboScribeBot:/app \
  abdlrhman00/turboscribe-bot-2:v4.0 \
  --id 701 \
  --output /hamada/TurboScribeBot/outputs/701 \
  --source onedrive \
  --link 'https://1drv.ms/v/c/abc123' \
  --with-transcription \
  --language ar \
  --translate en
```

**Full Pipeline: Transcribe + Summaries + Translation + Timestamps**

```bash
docker run -d --rm \
  -v /hamada/TurboScribeBot:/app \
  abdlrhman00/turboscribe-bot-2:v4.0 \
  --id 54 \
  --output /hamada/TurboScribeBot/outputs/54 \
  --link 'https://youtu.be/weaGPNlSMBE?si=im23gF5TOEG1U6ag' \
  --language ar \
  --short_summary \
  --detail_summary \
  --timestamps \
  --translate en
```
---

## 📜 License / Credits

* Developed by **Abdulrahman Muhammad**