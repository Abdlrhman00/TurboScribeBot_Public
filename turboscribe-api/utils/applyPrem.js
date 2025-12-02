const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);
const fs = require('fs-extra');
const dockerMonitor = require('./dockerMonitor');

async function applyJobPermissions(filePath, owner, group, permissions, containerId) {
  try {
    if (!await fs.pathExists(filePath)) {
      await fs.ensureDir(filePath);
    }

    const changes = [];

    // Apply initial permissions to directory
    if (owner || group) {
      const ownership = `${owner || ''}:${group || ''}`.replace(/^:|:$/g, '');
      await execPromise(`chown -R ${ownership} "${filePath}"`);
      if (owner) changes.push(`owner to ${owner}`);
      if (group) changes.push(`group to ${group}`);
    }

    if (permissions) {
      const permValue = parseInt(permissions, 8);
      await execPromise(`chmod -R ${permValue.toString(8)} "${filePath}"`);
      changes.push(`permissions to ${permValue.toString(8)}`);
    }

    console.log(`✅ Applied initial ${changes.join(', ')} to ${filePath}`);
    
    // Start background monitoring for container exit
    console.log(`🔍 Starting container monitoring for ${containerId}`);
    dockerMonitor.monitorContainerExit(containerId, filePath, owner, group, permissions)
      .then(result => {
        console.log(`🎉 Container ${containerId} completed - final permissions applied`);
      })
      .catch(error => {
        console.error(`💥 Container monitoring failed for ${containerId}:`, error.message);
      });
    
    return changes;

  } catch (error) {
    console.error('❌ Job permissions application failed:', error.message);
    throw error;
  }
}

module.exports = applyJobPermissions;