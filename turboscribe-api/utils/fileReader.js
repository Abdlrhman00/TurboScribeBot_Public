const fs = require('fs-extra');
const path = require('path');

class FileReader {
  async getJobStatus(jobId, hostOutputPath = null) {
    if (!hostOutputPath) {
      return { status: 'unknown', error: 'Output path not specified' };
    }

    const reportFile = path.join(hostOutputPath, `report_${jobId}.json`);
    
    try {
      // Check if job directory exists
      if (!await fs.pathExists(hostOutputPath)) {
        return { status: 'not_started', message: 'Job directory not found' };
      }

      // Check if report file exists (completed)
      if (await fs.pathExists(reportFile)) {
        try {
          const reportData = await fs.readJson(reportFile);
          return {
            status: 'completed',
            report: reportData,
            hostOutputPath: hostOutputPath,
            outputs: await this.getJobOutputs(jobId, hostOutputPath)
          };
        } catch (error) {
          return { 
            status: 'error', 
            error: `Failed to read report: ${error.message}` 
          };
        }
      }

      // Check if log file exists (in progress)
      const logFile = path.join(hostOutputPath, `${jobId}.log`);
      if (await fs.pathExists(logFile)) {
        const logStats = await fs.stat(logFile);
        const isRecent = (Date.now() - logStats.mtime.getTime()) < 300000; // 5 minutes
        return { 
          status: isRecent ? 'running' : 'stalled',
          hostOutputPath: hostOutputPath 
        };
      }

      return { status: 'starting', hostOutputPath: hostOutputPath };
    } catch (error) {
      return { status: 'error', error: error.message };
    }
  }

  async getJobLogs(jobId, hostOutputPath, lines = 50) {
    if (!hostOutputPath) {
      return { logs: '', error: 'Output path not specified' };
    }

    const logFile = path.join(hostOutputPath, `${jobId}.log`);
    
    try {
      if (!await fs.pathExists(logFile)) {
        return { logs: '', error: 'Log file not found' };
      }

      const logContent = await fs.readFile(logFile, 'utf8');
      const logLines = logContent.split('\n');
      
      // Get last N lines or full content
      const lastLines = lines > 0 ? 
        logLines.slice(-lines).join('\n') : 
        logContent;

      return { 
        logs: lastLines,
        totalLines: logLines.length,
        fileSize: (await fs.stat(logFile)).size,
        hostOutputPath: hostOutputPath
      };
    } catch (error) {
      return { logs: '', error: error.message };
    }
  }

  async getJobOutputs(jobId, hostOutputPath) {
    if (!hostOutputPath) {
      return { error: 'Output path not specified' };
    }
    
    try {
      if (!await fs.pathExists(hostOutputPath)) {
        return { error: 'Job directory not found' };
      }

      const files = await fs.readdir(hostOutputPath);
      const outputs = {
        files: {},
        report: null,
        log: null,
        hostPath: hostOutputPath
      };

      for (const file of files) {
        const filePath = path.join(hostOutputPath, file);
        const stats = await fs.stat(filePath);
        
        outputs.files[file] = {
          size: stats.size,
          modified: stats.mtime,
          path: filePath
        };

        // Special handling for report file
        if (file === `report_${jobId}.json`) {
          try {
            outputs.report = await fs.readJson(filePath);
          } catch (e) {
            outputs.report = { error: 'Failed to parse report file' };
          }
        }
        
        // Special handling for log file
        if (file === `${jobId}.log`) {
          outputs.log = {
            size: stats.size,
            lines: (await fs.readFile(filePath, 'utf8')).split('\n').length
          };
        }
      }

      return outputs;
    } catch (error) {
      return { error: error.message };
    }
  }

  async getReportData(jobId, hostOutputPath) {
    if (!hostOutputPath) {
      return { error: 'Output path not specified' };
    }

    const reportFile = path.join(hostOutputPath, `report_${jobId}.json`);
    
    try {
      if (!await fs.pathExists(reportFile)) {
        return { error: 'Report file not found' };
      }

      return await fs.readJson(reportFile);
    } catch (error) {
      return { error: error.message };
    }
  }

  async listAllJobs() {
    const defaultBase = process.env.OUTPUT_PATH || '/hamada/TurboScribeBot/outputs';
    
    try {
      if (!await fs.pathExists(defaultBase)) {
        return [];
      }

      const items = await fs.readdir(defaultBase);
      const jobs = [];

      for (const item of items) {
        const itemPath = path.join(defaultBase, item);
        const stats = await fs.stat(itemPath);
        
        if (stats.isDirectory()) {
          jobs.push({
            jobId: item,
            path: itemPath,
            created: stats.birthtime,
            modified: stats.mtime
          });
        }
      }

      return jobs;
    } catch (error) {
      throw new Error(`Failed to list jobs: ${error.message}`);
    }
  }
}

module.exports = new FileReader();