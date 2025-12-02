const express = require('express');
const router = express.Router();
const dockerManager = require('../utils/dockerManager');
const fileReader = require('../utils/fileReader');
const database = require('../utils/database');
const path = require('path'); 
const fs = require('fs-extra');
const applyJobPermissions = require('../utils/applyPrem')

// POST /api/jobs - Create new transcription job
router.post('/', async (req, res) => {
  try {
    const jobConfig = req.body;
    
    // Validate exactly like Python script
    const validationError = validateJobConfig(jobConfig);
    if (validationError) {
      return res.status(400).json({
        error: validationError
      });
    }

    // Check if job ID already exists in database
    if (jobConfig.id) {
      const existingJob = await database.getJob(jobConfig.id);
      if (existingJob) {
        return res.status(409).json({
          error: 'Job ID already exists',
          jobId: jobConfig.id,
          message: 'Please use a different job ID'
        });
      }
    }

    const result = await dockerManager.createJob(jobConfig);
    
    // Build file paths
    const outputPath = `${result.hostOutputPath}/${result.jobId}`;
    
    // Apply permissions with container monitoring
    if (jobConfig.owner || jobConfig.group || jobConfig.permissions) {
      await applyJobPermissions(
        outputPath, 
        jobConfig.owner, 
        jobConfig.group, 
        jobConfig.permissions,
        result.containerId // Pass container ID for monitoring
      );
    }
    
    // Save ONLY necessary fields to database
    await database.saveJob(result.jobId, outputPath);

    const response = {
      jobId: result.jobId,
      outputPath: outputPath,
      status: 'created',
      message: 'Job started successfully',
      timestamp: result.timestamp
    };

    // Include owner/permissions in response if provided
    if (jobConfig.owner || jobConfig.group || jobConfig.permissions) {
      response.owner = jobConfig.owner || 'unchanged';
      response.group = jobConfig.group || 'unchanged';
      response.permissions = jobConfig.permissions ? 
        parseInt(jobConfig.permissions, 8).toString(8) : 'unchanged';
      response.permissionsNote = 'Permissions will be finalized after job completion';
    }

    res.status(201).json(response);

  } catch (error) {
    console.error('Job creation error:', error);
    res.status(500).json({
      error: 'Failed to create job',
      details: error.message
    });
  }
});

// Validation function that matches Python script logic
function validateJobConfig(config) {
  // Check if ID is provided and not empty
  if (!config.id || config.id.trim() === '') {
    return "--id is required and cannot be empty";
  }
  
  // Check if source is provided (Zoom/OneDrive workflow)
  if (config.source) {
    // Zoom/OneDrive flow validation
    if (config.withTranscription && !config.language) {
      return "--language is required when using --with-transcription";
    }
    
    // For source workflow, link/file are not required in the same way
    // The Python script doesn't require them when source is specified
  } else {
    // Direct transcription workflow (no --source)
    if (!config.link && !config.file) {
      return "Must provide --link or --file if --source is not specified";
    }
    if (!config.language) {
      return "--language is required when using --link or --file";
    }
  }

  // Additional validations
  if (config.source && !['zoom', 'onedrive'].includes(config.source)) {
    return "--source must be either 'zoom' or 'onedrive'";
  }

  if (config.model && !['base', 'small', 'large-v2'].includes(config.model)) {
    return "--model must be one of: base, small, large-v2";
  }

  return null; // No errors
}

// GET /api/jobs/:jobId - Get job status and details
// router.get('/:jobId', async (req, res) => {
//   try {
//     const { jobId } = req.params;
//     const jobInfo = activeJobs.get(jobId);
    
//     if (!jobInfo) {
//       return res.status(404).json({ 
//         error: 'Job not found',
//         jobId: jobId
//       });
//     }

//     const status = await fileReader.getJobStatus(jobId, jobInfo.hostOutputPath);
    
//     res.json({
//       jobId,
//       ...status,
//       config: jobInfo.config,
//       createdAt: jobInfo.createdAt,
//       containerId: jobInfo.containerId,
//       timestamp: new Date().toISOString()
//     });
//   } catch (error) {
//     res.status(500).json({
//       error: 'Failed to fetch job status',
//       details: error.message
//     });
//   }
// });

// GET /api/jobs/:jobId/logs - Get job logs
router.get('/:jobId/logs', async (req, res) => {
  try {
    const { jobId } = req.params;
    const { lines, full } = req.query;
    
    const job = await database.getJob(jobId);
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    const lineCount = full ? 0 : parseInt(lines) || 50;
    const logResult = await fileReader.getJobLogs(jobId, job.output_path, lineCount);
    
    res.json({
      jobId,
      ...logResult,
      logPath: `${job.output_path}/${jobId}.log`,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to fetch logs',
      details: error.message
    });
  }
});

// GET /api/jobs/:jobId - Get job report specifically
router.get('/:jobId', async (req, res) => {
  try {
    const { jobId } = req.params;
    const job = await database.getJob(jobId);
    
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    const report = await fileReader.getReportData(jobId, job.output_path);
    
    if (report.error) {
      return res.status(404).json(report);
    }
    
    res.json({
      jobId,
      report,
      reportPath: `${job.output_path}/report_${jobId}.json`,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to fetch report',
      details: error.message
    });
  }
});

//GET /api/jobs - List all jobs
router.get('/', async (req, res) => {
  try {
    const jobs = await database.getAllJobs();
    
    res.json({ 
      jobs: jobs,
      total: jobs.length,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to fetch jobs',
      details: error.message
    });
  }
});

// GET /api/jobs/:jobId/outputs - Get all output files
// router.get('/:jobId/outputs', async (req, res) => {
//   try {
//     const { jobId } = req.params;
//     const jobInfo = activeJobs.get(jobId);
    
//     if (!jobInfo) {
//       return res.status(404).json({ error: 'Job not found' });
//     }

//     const outputs = await fileReader.getJobOutputs(jobId, jobInfo.hostOutputPath);
    
//     res.json({
//       jobId,
//       ...outputs,
//       timestamp: new Date().toISOString()
//     });
//   } catch (error) {
//     res.status(500).json({
//       error: 'Failed to fetch outputs',
//       details: error.message
//     });
//   }
// });

// DELETE /api/jobs/:jobId - Cancel job
router.delete('/:jobId', async (req, res) => {
  try {
    const { jobId } = req.params;
    const job = await database.getJob(jobId);
    
    if (!job) {
      return res.status(404).json({ error: 'Job not found' });
    }

    // Get the folder path from the report path or log path
    const folderPath = job.output_path;
    
    // Delete the job from database
    await database.deleteJob(jobId);
    
    // Delete the folder and all its contents
    let folderDeleted = false;
    try {
      if (await fs.pathExists(folderPath)) {
        await fs.remove(folderPath);
        folderDeleted = true;
      }
    } catch (folderError) {
      console.warn(`Could not delete folder ${folderPath}:`, folderError.message);
      // Continue even if folder deletion fails
    }
    
    res.json({
      jobId,
      status: 'deleted',
      message: folderDeleted 
        ? 'Job removed from database and folder deleted' 
        : 'Job removed from database (folder may not exist)',
      folderPath: folderPath,
      folderDeleted: folderDeleted,
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    res.status(500).json({
      error: 'Failed to delete job',
      details: error.message
    });
  }
});

// DELETE /api/jobs - Delete ALL jobs but keep directory structure
router.delete('/', async (req, res) => {
    try {
        const { confirm } = req.query;
        
        if (confirm !== 'true') {
            return res.status(400).json({
                error: 'Confirmation required',
                message: 'Add ?confirm=true to confirm deletion of all jobs'
            });
        }

        const defaultOutputBase = process.env.OUTPUT_PATH;
        
        // Delete all jobs from database
        const deletedCount = await database.deleteAllJobs();
        
        // Delete all job subdirectories but keep the base directory
        let foldersDeleted = 0;
        try {
            if (await fs.pathExists(defaultOutputBase)) {
                const items = await fs.readdir(defaultOutputBase);
                
                for (const item of items) {
                    const itemPath = path.join(defaultOutputBase, item);
                    const stats = await fs.stat(itemPath);
                    
                    if (stats.isDirectory()) {
                        await fs.remove(itemPath);
                        foldersDeleted++;
                    }
                }
            }
        } catch (folderError) {
            console.warn(`Could not clean output directory ${defaultOutputBase}:`, folderError.message);
        }
        
        res.json({
            status: 'deleted_all',
            message: `All jobs (${deletedCount}) removed from database and ${foldersDeleted} job directories cleaned`,
            jobsDeleted: deletedCount,
            foldersCleaned: foldersDeleted,
            folderPath: defaultOutputBase,
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        console.error('Delete all jobs error:', error);
        res.status(500).json({
            error: 'Failed to delete all jobs',
            details: error.message
        });
    }
});


// Export only the router for middleware
module.exports = router;