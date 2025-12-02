# 🚀 TurboScribeBot Backend API

## 📋 Project Overview

TurboScribeBot Backend API provides a robust RESTful interface for managing audio and video transcription jobs. It simplifies interactions with the TurboScribeBot automation tool by wrapping complex Docker commands in easy-to-use API endpoints.

**Problem Solved:**
Managing transcription tasks manually using Docker commands is error-prone and inefficient, especially for batch processing or automation workflows.

**High-Level Solution:**
This backend exposes a clean, RESTful API that allows users to create, monitor, and manage transcription jobs, handle files, and configure output permissions—all programmatically.

**Unique Value Proposition:**

* Abstracts Docker orchestration complexity
* Centralized management of transcription jobs
* Flexible workflow support: YouTube, Zoom, OneDrive, and local files
* Permissions and ownership management for output files

---

## 🛠️ Technologies & Tools Used

* **Programming Languages:** Node.js, JavaScript
* **Frameworks & Libraries:** Express.js, fs-extra, Dockerode, uuid
* **Containerization:** Docker
* **Process Management:** PM2
* **Transcription & AI:** TurboScribeBot automation script
* **API Security:** API key authentication
* **DevOps / Deployment:** Linux (CentOS/Fedora), Node.js runtime, PM2 process manager

---

## 🌟 Key Achievements / Highlights

* Fully automated job orchestration using Docker containers
* API endpoints for creating, deleting, and monitoring transcription jobs
* Support for multiple transcription workflows (Zoom, OneDrive, YouTube, local files)
* Detailed job reports, logs, and structured output management
* File system operations with ownership and permissions handling (copy, move, chown)
* Robust error handling and consistent API responses
* Streamlined deployment with PM2 and Docker integration

---

## 💡 Skills Demonstrated

**Technical Skills:**

* Node.js backend development
* RESTful API design and implementation
* Docker container orchestration via Node.js
* File system operations and permissions handling
* Process management using PM2
* Environment configuration and deployment automation

**Soft Skills:**

* Problem-solving and workflow optimization
* Writing clear documentation and API specifications
* Designing scalable and maintainable systems

---

## ⚙️ Installation & Setup

### Prerequisites

* **Node.js 18**
* **Docker CE**
* **PM2 process manager**
* Linux system (CentOS/Fedora recommended)

### Install Required Software

```bash
sudo dnf update -y
sudo dnf install -y epel-release
sudo dnf config-manager --add-repo=https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo dnf install -y nodejs
sudo npm install -g pm2
```

### Verify Installations

```bash
docker --version
node --version
npm --version
pm2 --version
```

### Environment Configuration

**Credentials `.env` file (TurboScribeBot):**

```env
EMAIL=your-email@example.com
PASSWORD=your-password-here
```

**Backend API `.env` file (TurboScribe API):**

```env
PORT=3000
OUTPUT_PATH=/opt/turboscribe/TurboScribeBot/outputs
ENV_FILE_PATH=/opt/turboscribe/TurboScribeBot/.env
API_KEYS=your-secret-key-123,another-key-456
```

### Build Docker Image

### 1️⃣ Build the Docker Container

```bash
cd /path/to/TurboScribeBot
docker build -t abdlrhman00/turboscribe-bot-2:v4.0 .
docker images | grep turboscribe
```

### 2️⃣ Pull from DockerHub (Private Repo)

```bash
docker pull abdlrhman00/turboscribe-bot-2:v4.0
```

### Backend Server Setup with PM2

```bash
cd /path/to/turboscribe-api
npm install
```

**PM2 Configuration (`turbo.config.js`):**

```javascript
module.exports = {
  apps: [{
    name: 'turboscribe-api',
    script: 'server.js',
    env: { NODE_ENV: 'production' }
  }]
};
```

**Start Application:**

```bash
pm2 start turbo.config.js
pm2 save
pm2 startup
```

**Verify Deployment:**

```bash
curl -H "x-api-key: your-secret-key-123" http://localhost:3000/health
```

---

## 📖 Usage Guide

### Health Check

```bash
curl -H "x-api-key: your-secret-key-123" http://localhost:3000/health
```

### Create a Job

**Request Body**:
```json
{
  "id": "string (required - unique)",              // Custom job ID
  "output": "string (optional)",          // Custom output directory path
  "source": "zoom|onedrive (optional)",   // Source type for Zoom/OneDrive workflow
  
  // Source workflow parameters (when using source)
  "link": "string (optional)",            // Source URL
  "passcode": "string (optional)",        // Zoom recording passcode
  "withTranscription": "boolean",         // Auto-transcribe after download
  
  // Direct transcription parameters (when no source)
  "link": "string",                       // YouTube/audio/video URL
  "file": "string",                       // Local file path
  "language": "string (required)",        // Transcription language (en, ar, etc.)
  
  // Transcription options
  "model": "base|small|large-v2",         // Model size (default: base)
  
  // Feature flags
  "speakers": "number|boolean",           // Speaker recognition (-1 for auto, number for count)
  "transcribe": "boolean",                // Enable transcription
  "restore": "boolean",                   // Restore audio quality
  "timestamps": "boolean",                // Add timestamps to output
  "shortSummary": "boolean",              // Generate short summary
  "detailSummary": "boolean",             // Generate detailed summary
  "translate": "string",                  // Translate to language code
  "downloadAudio": "boolean",             // Download original audio file
  
  // File permissions (applied after job completion)
  "owner": "string (optional)",           // Set output directory owner
  "group": "string (optional)",           // Set output directory group
  "permissions": "string (optional)"      // Octal permissions (e.g., "755")
}
```

```bash
curl -X POST http://localhost:3000/api/jobs \
  -H "x-api-key: your-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "50",
    "link": "https://youtu.be/weaGPNlSMBE",
    "language": "ar",
    "owner": "testuser"
  }'
```

### List Jobs

```bash
curl -H "x-api-key: your-secret-key-123" http://localhost:3000/api/jobs
```

### Get Job Details

```bash
curl -H "x-api-key: your-secret-key-123" http://localhost:3000/api/jobs/job-123
```

### Get Job Logs

```bash
curl -H "x-api-key: your-secret-key-123" "http://localhost:3000/api/jobs/job-123/logs?lines=50"
```

### Delete a Job

```bash
curl -X DELETE -H "x-api-key: your-secret-key-123" http://localhost:3000/api/jobs/job-123
```

### File Operations Examples

**Copy File**

```bash
curl -X POST http://localhost:3000/api/files/copy \
  -H "x-api-key: your-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "sourcePath": "/tmp/source.txt",
    "destinationPath": "/tmp/dest.txt",
    "owner": "www-data",
    "permissions": "644"
  }'
```

**Change Ownership**

```bash
curl -X POST http://localhost:3000/api/files/chown \
  -H "x-api-key: your-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/var/www/html",
    "owner": "www-data",
    "permissions": "755",
    "recursive": true
  }'
```

**Move File**

```bash
curl -X POST http://localhost:3000/api/files/move \
  -H "x-api-key: your-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "sourcePath": "/tmp/old-file.txt",
    "destinationPath": "/tmp/new-file.txt",
    "owner": "www-data"
  }'
```

---

## 📂 Outputs / Results

* Output files stored in the configured `OUTPUT_PATH` directory
* Each job has its own folder: `/outputs/{jobId}/`
* Generated files include:

  * Transcription `.txt`
  * Job report `.json`
  * Logs `.log`
  * Optional audio download

**Example Folder Structure:**

```
/TurboScribeBot/outputs/
├── job-123/
│   ├── transcription.txt
│   ├── report_job-123.json
│   ├── job-123.log
│   └── original_audio.mp3
```

---

## 🖥️ Example Use Cases

* Transcribe YouTube videos with short and detailed summaries
* Download and transcribe Zoom recordings automatically
* Manage local audio files and apply speaker recognition
* Batch processing multiple transcription jobs programmatically
* File operations with automated ownership and permissions

---

## 📜 License / Credits

* Developed by **Abdulrahman Muhammad**