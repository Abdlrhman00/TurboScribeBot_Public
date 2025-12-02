const Docker = require('dockerode');
const docker = new Docker();
const { v4: uuidv4 } = require('uuid');
const path = require('path');
const fs = require('fs-extra');

class DockerManager {
  constructor() {
    this.envFilePath = process.env.ENV_FILE_PATH || '/hamada/TurboScribeBot/.env';
    this.defaultOutputBase = process.env.OUTPUT_PATH || '/hamada/TurboScribeBot/outputs';
  }

  async createJob(jobConfig) {
    const jobId = jobConfig.id || uuidv4();
    
    // Determine output path
    let hostOutputPath = jobConfig.output;
    if (!hostOutputPath) {
      hostOutputPath = path.join(this.defaultOutputBase, jobId);
    }

    // Use same path inside container
    const containerOutputPath = hostOutputPath;

    try {
      // Ensure output directory exists
      await fs.ensureDir(hostOutputPath);

      // Build command and prepare mounts
      const command = this.buildCommand(jobId, containerOutputPath, jobConfig);
      const binds = this.prepareVolumeBinds(hostOutputPath, containerOutputPath, jobConfig);

      const container = await docker.createContainer({
        Image: 'abdlrhman00/turboscribe-bot-2:v4.0',
        Cmd: command,
        HostConfig: {
          Binds: binds,
          AutoRemove: true
        },
        AttachStdout: true,
        AttachStderr: true
      });

      await container.start();
      
      return {
        jobId,
        containerId: container.id,
        hostOutputPath: hostOutputPath,
        containerOutputPath: containerOutputPath,
        status: 'created',
        command: command.join(' '),
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      throw new Error(`Docker container creation failed: ${error.message}`);
    }
  }

  prepareVolumeBinds(hostOutputPath, containerOutputPath, jobConfig) {
    const binds = [
      `${this.envFilePath}:/app/.env:ro`,
    ];

    // Mount output directory parent to maintain path structure
    const outputParent = path.dirname(hostOutputPath);
    const containerParent = path.dirname(containerOutputPath);
    
    binds.push(`${outputParent}:${containerParent}:rw`);

    // Handle local file mounting
    if (jobConfig.file && path.isAbsolute(jobConfig.file)) {
      const fileDir = path.dirname(jobConfig.file);
      const fileName = path.basename(jobConfig.file);
      const containerFileDir = '/app/input_files';
      
      binds.push(`${fileDir}:${containerFileDir}:ro`);
    }

    return binds;
  }

  buildCommand(jobId, containerOutputPath, config) {
    const args = [
      '--id', jobId,
      '--output', containerOutputPath
    ];

    // Source workflow (Zoom/OneDrive)
    if (config.source) {
      args.push('--source', config.source);
      if (config.passcode) args.push('--passcode', config.passcode);
      if (config.link) args.push('--link', config.link);
      if (config.withTranscription) args.push('--with-transcription');
    }

    // Direct transcription workflow (only if no source)
    if (!config.source) {
      if (config.link) {
        args.push('--link', config.link);
      } else if (config.file) {
        // Adjust path for container if absolute path
        if (path.isAbsolute(config.file)) {
          const fileName = path.basename(config.file);
          const containerFilePath = path.join('/app/input_files', fileName);
          args.push('--file', containerFilePath);
        } else {
          args.push('--file', config.file);
        }
      }
    }

    // Options
    if (config.language) args.push('--language', config.language);
    if (config.model) args.push('--model', config.model);

    // Features (flags)
    if (config.speakers !== undefined) {
      if (config.speakers === -1 || config.speakers === true) {
        args.push('--speakers');
      } else {
        args.push('--speakers', config.speakers.toString());
      }
    }
    if (config.transcribe) args.push('--transcribe');
    if (config.restore) args.push('--restore');
    if (config.timestamps) args.push('--timestamps');
    if (config.shortSummary) args.push('--short_summary');
    if (config.detailSummary) args.push('--detail_summary');
    if (config.translate) args.push('--translate', config.translate);
    if (config.downloadAudio) args.push('--download_audio');

    return args;
  }

  async getContainerStatus(containerId) {
    try {
      const container = docker.getContainer(containerId);
      const data = await container.inspect();
      return data.State.Status;
    } catch (error) {
      return 'not_found';
    }
  }

  async stopJob(containerId) {
    try {
      const container = docker.getContainer(containerId);
      await container.stop();
      return true;
    } catch (error) {
      throw new Error(`Failed to stop container: ${error.message}`);
    }
  }
}

module.exports = new DockerManager();