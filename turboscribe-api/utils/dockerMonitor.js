const Docker = require('dockerode');
const docker = new Docker();
const { exec } = require('child_process');
const util = require('util');
const execPromise = util.promisify(exec);

class DockerMonitor {
  // Monitor container exit and apply permissions
  async monitorContainerExit(containerId, filePath, owner, group, permissions) {
    try {
      console.log(`🔍 Monitoring container ${containerId} for exit...`);
      
      const container = docker.getContainer(containerId);
      
      // Wait for container to exit (blocks until container stops)
      const exitData = await container.wait();
      console.log(`✅ Container ${containerId} exited with status: ${exitData.StatusCode}`);
      
      // Wait 3 seconds for file system to settle
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Apply final permissions to all files created by container
      await this.applyFinalPermissions(filePath, owner, group, permissions);
      console.log(`✅ Final permissions applied to ${filePath}`);
      
      return {
        success: true,
        containerId,
        exitCode: exitData.StatusCode
      };
      
    } catch (error) {
      console.error(`❌ Container monitoring failed for ${containerId}:`, error.message);
      throw error;
    }
  }

  // Apply permissions to all files after container exit
  async applyFinalPermissions(filePath, owner, group, permissions) {
    if (!await require('fs-extra').pathExists(filePath)) {
      throw new Error(`Directory ${filePath} does not exist`);
    }

    const changes = [];
    
    // Change ownership
    if (owner || group) {
      const ownership = `${owner || ''}:${group || ''}`.replace(/^:|:$/g, '');
      await execPromise(`chown -R ${ownership} "${filePath}"`);
      if (owner) changes.push(`owner to ${owner}`);
      if (group) changes.push(`group to ${group}`);
    }
    
    // Set permissions
    if (permissions) {
      const permValue = parseInt(permissions, 8);
      await execPromise(`chmod -R ${permValue.toString(8)} "${filePath}"`);
      changes.push(`permissions to ${permValue.toString(8)}`);
    }
    
    return changes;
  }
}

module.exports = new DockerMonitor();