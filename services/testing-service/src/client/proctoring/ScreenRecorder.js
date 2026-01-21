/**
 * Screen recording system with WebRTC
 * Requirements: 5.2
 */

class ScreenRecorder {
  constructor(options = {}) {
    this.options = {
      videoBitsPerSecond: 2500000, // 2.5 Mbps
      audioBitsPerSecond: 128000,  // 128 kbps
      mimeType: 'video/webm;codecs=vp9',
      chunkDuration: 10000, // 10 seconds per chunk
      maxChunkSize: 5 * 1024 * 1024, // 5MB max chunk size
      compressionQuality: 0.8,
      uploadEndpoint: '/api/proctoring/upload-chunk',
      ...options
    };

    this.mediaRecorder = null;
    this.stream = null;
    this.isRecording = false;
    this.isPaused = false;
    this.chunks = [];
    this.chunkIndex = 0;
    this.sessionId = null;
    this.uploadQueue = [];
    this.isUploading = false;
    this.recordingStartTime = null;
    this.lastChunkTime = null;

    this.onError = options.onError || (() => { });
    this.onChunkReady = options.onChunkReady || (() => { });
    this.onUploadProgress = options.onUploadProgress || (() => { });
  }

  /**
   * Initialize screen recording
   */
  async initialize(sessionId) {
    try {
      this.sessionId = sessionId;

      // Check browser support
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        throw new Error('Screen recording not supported in this browser');
      }

      // Check MediaRecorder support
      if (!window.MediaRecorder) {
        throw new Error('MediaRecorder not supported in this browser');
      }

      // Check codec support
      if (!MediaRecorder.isTypeSupported(this.options.mimeType)) {
        // Fallback to webm
        this.options.mimeType = 'video/webm';
        if (!MediaRecorder.isTypeSupported(this.options.mimeType)) {
          // Final fallback
          this.options.mimeType = '';
        }
      }

      return { success: true, message: 'Screen recorder initialized' };

    } catch (error) {
      this.onError(error);
      return { success: false, message: error.message };
    }
  }

  /**
   * Start screen recording
   */
  async startRecording() {
    try {
      if (this.isRecording) {
        return { success: false, message: 'Recording already in progress' };
      }

      // Request screen capture permission
      this.stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          mediaSource: 'screen',
          width: { ideal: 1920, max: 1920 },
          height: { ideal: 1080, max: 1080 },
          frameRate: { ideal: 30, max: 30 }
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      });

      // Create MediaRecorder
      const mediaRecorderOptions = {
        mimeType: this.options.mimeType,
        videoBitsPerSecond: this.options.videoBitsPerSecond,
        audioBitsPerSecond: this.options.audioBitsPerSecond
      };

      this.mediaRecorder = new MediaRecorder(this.stream, mediaRecorderOptions);

      // Set up event handlers
      this.setupEventHandlers();

      // Start recording
      this.mediaRecorder.start(this.options.chunkDuration);
      this.isRecording = true;
      this.recordingStartTime = new Date();
      this.lastChunkTime = this.recordingStartTime;

      // Monitor stream status
      this.monitorStream();

      console.log('Screen recording started');

      return {
        success: true,
        message: 'Screen recording started',
        mimeType: this.options.mimeType
      };

    } catch (error) {
      this.onError(error);
      return { success: false, message: error.message };
    }
  }

  /**
   * Stop screen recording
   */
  async stopRecording() {
    try {
      if (!this.isRecording) {
        return { success: false, message: 'No recording in progress' };
      }

      // Stop MediaRecorder
      if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
        this.mediaRecorder.stop();
      }

      // Stop all tracks
      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
        this.stream = null;
      }

      this.isRecording = false;
      this.isPaused = false;

      // Upload any remaining chunks
      await this.uploadRemainingChunks();

      console.log('Screen recording stopped');

      return { success: true, message: 'Screen recording stopped' };

    } catch (error) {
      this.onError(error);
      return { success: false, message: error.message };
    }
  }

  /**
   * Pause screen recording
   */
  pauseRecording() {
    try {
      if (!this.isRecording || this.isPaused) {
        return { success: false, message: 'Cannot pause recording' };
      }

      if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
        this.mediaRecorder.pause();
        this.isPaused = true;
      }

      return { success: true, message: 'Recording paused' };

    } catch (error) {
      this.onError(error);
      return { success: false, message: error.message };
    }
  }

  /**
   * Resume screen recording
   */
  resumeRecording() {
    try {
      if (!this.isRecording || !this.isPaused) {
        return { success: false, message: 'Cannot resume recording' };
      }

      if (this.mediaRecorder && this.mediaRecorder.state === 'paused') {
        this.mediaRecorder.resume();
        this.isPaused = false;
      }

      return { success: true, message: 'Recording resumed' };

    } catch (error) {
      this.onError(error);
      return { success: false, message: error.message };
    }
  }

  /**
   * Set up MediaRecorder event handlers
   */
  setupEventHandlers() {
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        this.handleChunk(event.data);
      }
    };

    this.mediaRecorder.onstart = () => {
      console.log('MediaRecorder started');
    };

    this.mediaRecorder.onstop = () => {
      console.log('MediaRecorder stopped');
    };

    this.mediaRecorder.onpause = () => {
      console.log('MediaRecorder paused');
    };

    this.mediaRecorder.onresume = () => {
      console.log('MediaRecorder resumed');
    };

    this.mediaRecorder.onerror = (event) => {
      console.error('MediaRecorder error:', event.error);
      this.onError(event.error);
    };
  }

  /**
   * Handle recorded chunk
   */
  async handleChunk(blob) {
    try {
      const now = new Date();
      const chunkInfo = {
        index: this.chunkIndex++,
        blob: blob,
        size: blob.size,
        timestamp: now,
        duration: now.getTime() - this.lastChunkTime.getTime(),
        sessionId: this.sessionId
      };

      this.lastChunkTime = now;

      // Compress chunk if needed
      const processedChunk = await this.processChunk(chunkInfo);

      // Add to upload queue
      this.uploadQueue.push(processedChunk);

      // Trigger chunk ready callback
      this.onChunkReady(processedChunk);

      // Start upload if not already uploading
      if (!this.isUploading) {
        this.processUploadQueue();
      }

    } catch (error) {
      console.error('Error handling chunk:', error);
      this.onError(error);
    }
  }

  /**
   * Process and compress chunk
   */
  async processChunk(chunkInfo) {
    try {
      let processedBlob = chunkInfo.blob;

      // Check if chunk is too large
      if (chunkInfo.size > this.options.maxChunkSize) {
        // Compress the chunk
        processedBlob = await this.compressChunk(chunkInfo.blob);
      }

      return {
        ...chunkInfo,
        blob: processedBlob,
        size: processedBlob.size,
        compressed: processedBlob !== chunkInfo.blob,
        originalSize: chunkInfo.size
      };

    } catch (error) {
      console.warn('Chunk processing failed, using original:', error);
      return chunkInfo;
    }
  }

  /**
   * Compress video chunk
   */
  async compressChunk(blob) {
    return new Promise((resolve) => {
      // For now, return original blob
      // In a real implementation, you might use a library like FFmpeg.js
      // or reduce quality settings
      resolve(blob);
    });
  }

  /**
   * Process upload queue
   */
  async processUploadQueue() {
    if (this.isUploading || this.uploadQueue.length === 0) {
      return;
    }

    this.isUploading = true;

    while (this.uploadQueue.length > 0) {
      const chunk = this.uploadQueue.shift();

      try {
        await this.uploadChunk(chunk);
      } catch (error) {
        console.error('Chunk upload failed:', error);
        // Re-queue the chunk for retry
        this.uploadQueue.unshift(chunk);
        break;
      }
    }

    this.isUploading = false;
  }

  /**
   * Upload chunk to server
   */
  async uploadChunk(chunkInfo) {
    try {
      const formData = new FormData();
      formData.append('chunk', chunkInfo.blob);
      formData.append('sessionId', chunkInfo.sessionId);
      formData.append('chunkIndex', chunkInfo.index.toString());
      formData.append('timestamp', chunkInfo.timestamp.toISOString());
      formData.append('duration', chunkInfo.duration.toString());
      formData.append('size', chunkInfo.size.toString());

      if (chunkInfo.compressed) {
        formData.append('compressed', 'true');
        formData.append('originalSize', chunkInfo.originalSize.toString());
      }

      const response = await fetch(this.options.uploadEndpoint, {
        method: 'POST',
        body: formData,
        headers: {
          'X-Session-ID': this.sessionId
        }
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
      }

      const result = await response.json();

      // Update progress
      this.onUploadProgress({
        chunkIndex: chunkInfo.index,
        uploaded: true,
        size: chunkInfo.size,
        timestamp: chunkInfo.timestamp
      });

      console.log(`Chunk ${chunkInfo.index} uploaded successfully`);

      return result;

    } catch (error) {
      console.error(`Failed to upload chunk ${chunkInfo.index}:`, error);
      throw error;
    }
  }

  /**
   * Upload remaining chunks
   */
  async uploadRemainingChunks() {
    const maxRetries = 3;
    let retries = 0;

    while (this.uploadQueue.length > 0 && retries < maxRetries) {
      try {
        await this.processUploadQueue();
        break;
      } catch (error) {
        retries++;
        console.warn(`Upload retry ${retries}/${maxRetries}:`, error);

        if (retries < maxRetries) {
          // Wait before retry
          await new Promise(resolve => setTimeout(resolve, 1000 * retries));
        }
      }
    }

    if (this.uploadQueue.length > 0) {
      console.error(`Failed to upload ${this.uploadQueue.length} chunks after ${maxRetries} retries`);
    }
  }

  /**
   * Monitor stream status
   */
  monitorStream() {
    if (!this.stream) return;

    // Monitor if user stops sharing screen
    this.stream.getVideoTracks().forEach(track => {
      track.onended = () => {
        console.warn('Screen sharing ended by user');
        this.handleStreamEnded();
      };
    });

    // Monitor audio tracks
    this.stream.getAudioTracks().forEach(track => {
      track.onended = () => {
        console.warn('Audio sharing ended');
      };
    });
  }

  /**
   * Handle stream ended
   */
  handleStreamEnded() {
    if (this.isRecording) {
      console.log('Stream ended, stopping recording');
      this.stopRecording();

      // Notify about violation
      this.onError(new Error('Screen sharing was stopped by user'));
    }
  }

  /**
   * Get recording status
   */
  getStatus() {
    return {
      isRecording: this.isRecording,
      isPaused: this.isPaused,
      recordingDuration: this.recordingStartTime ?
        new Date().getTime() - this.recordingStartTime.getTime() : 0,
      chunksRecorded: this.chunkIndex,
      chunksInQueue: this.uploadQueue.length,
      isUploading: this.isUploading,
      streamActive: this.stream && this.stream.active
    };
  }

  /**
   * Get recording statistics
   */
  getStatistics() {
    const status = this.getStatus();

    return {
      ...status,
      averageChunkSize: this.chunkIndex > 0 ?
        this.chunks.reduce((sum, chunk) => sum + chunk.size, 0) / this.chunkIndex : 0,
      totalDataRecorded: this.chunks.reduce((sum, chunk) => sum + chunk.size, 0),
      recordingQuality: this.options.videoBitsPerSecond,
      mimeType: this.options.mimeType
    };
  }

  /**
   * Cleanup resources
   */
  cleanup() {
    try {
      if (this.isRecording) {
        this.stopRecording();
      }

      if (this.stream) {
        this.stream.getTracks().forEach(track => track.stop());
        this.stream = null;
      }

      this.mediaRecorder = null;
      this.chunks = [];
      this.uploadQueue = [];
      this.isRecording = false;
      this.isPaused = false;
      this.isUploading = false;

    } catch (error) {
      console.error('Cleanup error:', error);
    }
  }
}

// Export for use in browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = ScreenRecorder;
} else if (typeof window !== 'undefined') {
  window.ScreenRecorder = ScreenRecorder;
}