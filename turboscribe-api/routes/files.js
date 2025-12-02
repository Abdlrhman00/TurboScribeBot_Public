const express = require('express');
const fs = require('fs-extra');
const { exec } = require('child_process');
const util = require('util');
const router = express.Router();

const execPromise = util.promisify(exec);

// POST /api/files/copy - Copy files between accounts with ownership change
router.post('/copy', async (req, res) => {
  try {
    const { sourcePath, destinationPath, owner, group, permissions } = req.body;

    if (!sourcePath || !destinationPath) {
      return res.status(400).json({
        error: 'sourcePath and destinationPath are required'
      });
    }

    // Check if source exists
    if (!await fs.pathExists(sourcePath)) {
      return res.status(404).json({
        error: 'Source path not found',
        sourcePath: sourcePath
      });
    }

    // Ensure destination directory exists
    const path = require('path');
    await fs.ensureDir(path.dirname(destinationPath));

    // Copy file or directory
    await fs.copy(sourcePath, destinationPath);

    // Change ownership if specified
    if (owner || group) {
      const ownership = `${owner || ''}:${group || ''}`.replace(/^:|:$/g, '');
      if (ownership) {
        try {
          await execPromise(`chown -R ${ownership} "${destinationPath}"`);
        } catch (chownError) {
          console.warn(`Ownership change failed for ${destinationPath}:`, chownError.message);
          // Continue even if ownership change fails
        }
      }
    }

    // Set permissions if specified
    if (permissions) {
      try {
        await fs.chmod(destinationPath, parseInt(permissions, 8));
        
        // If it's a directory, apply recursively
        const stats = await fs.stat(destinationPath);
        if (stats.isDirectory()) {
          await execPromise(`chmod -R ${permissions} "${destinationPath}"`);
        }
      } catch (chmodError) {
        console.warn(`Permissions change failed for ${destinationPath}:`, chmodError.message);
      }
    }

    // Get final file stats
    const stats = await fs.stat(destinationPath);
    const finalStats = await execPromise(`ls -ld "${destinationPath}"`).catch(() => ({ stdout: 'N/A' }));

    res.json({
      status: 'success',
      message: 'File copied successfully with ownership changes',
      sourcePath,
      destinationPath,
      owner: owner || 'unchanged',
      group: group || 'unchanged',
      permissions: permissions ? permissions.toString(8) : 'unchanged',
      size: stats.size,
      finalStats: finalStats.stdout.trim(),
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    res.status(500).json({
      error: 'File copy failed',
      details: error.message
    });
  }
});

// POST /api/files/chown - Change ownership and/or permissions
router.post('/chown', async (req, res) => {
  try {
    const { 
      path: filePath, 
      owner, 
      group, 
      permissions,
      recursive = true 
    } = req.body;

    if (!filePath) {
      return res.status(400).json({
        error: 'path is required'
      });
    }

    if (!owner && !group && !permissions) {
      return res.status(400).json({
        error: 'Either owner, group, or permissions must be specified'
      });
    }

    // Check if path exists
    if (!await fs.pathExists(filePath)) {
      return res.status(404).json({
        error: 'Path not found',
        path: filePath
      });
    }

    const changes = [];
    const recursiveFlag = recursive ? '-R' : '';

    // Change ownership if specified
    if (owner || group) {
      const ownership = `${owner || ''}:${group || ''}`.replace(/^:|:$/g, '');
      if (ownership) {
        try {
          await execPromise(`sudo chown ${recursiveFlag} ${ownership} "${filePath}"`);
          if (owner) changes.push(`owner to ${owner}`);
          if (group) changes.push(`group to ${group}`);
        } catch (chownError) {
          console.warn(`Ownership change failed for ${filePath}:`, chownError.message);
          throw new Error(`Ownership change failed: ${chownError.message}`);
        }
      }
    }

    // Set permissions if specified
    if (permissions) {
      try {
        const permValue = parseInt(permissions, 8);
        
        if (recursive) {
          // For recursive, use find command for better control
          await execPromise(`find "${filePath}" -type f -exec chmod ${permValue.toString(8)} {} +`);
          await execPromise(`find "${filePath}" -type d -exec chmod ${(permValue | 0o111).toString(8)} {} +`);
        } else {
          await fs.chmod(filePath, permValue);
        }
        
        changes.push(`permissions to ${permValue.toString(8)}`);
      } catch (chmodError) {
        console.warn(`Permissions change failed for ${filePath}:`, chmodError.message);
        throw new Error(`Permissions change failed: ${chmodError.message}`);
      }
    }

    // Get new file stats
    const stats = await fs.stat(filePath);
    const newStats = await execPromise(`ls -ld "${filePath}"`);

    const message = changes.length > 0 
      ? `Changed ${changes.join(', ')} successfully${recursive ? ' (recursively)' : ''}`
      : 'No changes made';

    res.json({
      status: 'success',
      message: message,
      path: filePath,
      changes: {
        owner: owner || 'unchanged',
        group: group || 'unchanged',
        permissions: permissions ? parseInt(permissions, 8).toString(8) : 'unchanged'
      },
      recursive: recursive,
      fileInfo: {
        isDirectory: stats.isDirectory(),
        size: stats.size,
        modified: stats.mtime,
        detailed: newStats.stdout.trim()
      },
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    res.status(500).json({
      error: 'File modification failed',
      details: error.message
    });
  }
});

// POST /api/files/move - Move files with ownership change
router.post('/move', async (req, res) => {
  try {
    const { sourcePath, destinationPath, owner, group, permissions } = req.body;

    if (!sourcePath || !destinationPath) {
      return res.status(400).json({
        error: 'sourcePath and destinationPath are required'
      });
    }

    // Check if source exists
    if (!await fs.pathExists(sourcePath)) {
      return res.status(404).json({
        error: 'Source path not found',
        sourcePath: sourcePath
      });
    }

    // Ensure destination directory exists
    const path = require('path');
    await fs.ensureDir(path.dirname(destinationPath));

    // Move file or directory
    await fs.move(sourcePath, destinationPath);

    // Change ownership if specified
    if (owner || group) {
      const ownership = `${owner || ''}:${group || ''}`.replace(/^:|:$/g, '');
      if (ownership) {
        try {
          await execPromise(`chown -R ${ownership} "${destinationPath}"`);
        } catch (chownError) {
          console.warn(`Ownership change failed:`, chownError.message);
        }
      }
    }

    // Set permissions if specified
    if (permissions) {
      try {
        await fs.chmod(destinationPath, parseInt(permissions, 8));
      } catch (chmodError) {
        console.warn(`Permissions change failed:`, chmodError.message);
      }
    }

    res.json({
      status: 'success',
      message: 'File moved successfully with ownership changes',
      sourcePath,
      destinationPath,
      owner: owner || 'unchanged',
      group: group || 'unchanged',
      permissions: permissions ? permissions.toString(8) : 'unchanged',
      timestamp: new Date().toISOString()
    });

  } catch (error) {
    res.status(500).json({
      error: 'File move failed',
      details: error.message
    });
  }
});

module.exports = router;