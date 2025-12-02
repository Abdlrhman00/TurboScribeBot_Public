const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs-extra');

class Database {
  constructor() {
    this.dbPath = path.join(__dirname, '..', 'turboscribe.db');
    this.init();
  }

  init() {
    // Ensure database directory exists
    const dbDir = path.dirname(this.dbPath);
    fs.ensureDirSync(dbDir);

    this.db = new sqlite3.Database(this.dbPath, (err) => {
      if (err) {
        console.error('Error opening database:', err.message);
      } else {
        console.log('Connected to SQLite database.');
        this.createTable();
      }
    });
  }

  createTable() {
    const sql = `
      CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        output_path TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `;

    this.db.run(sql, (err) => {
      if (err) {
        console.error('Error creating jobs table:', err.message);
      } else {
        console.log('Jobs table ready.');
      }
    });
  }

  // Save job with paths
  saveJob(jobId, outputPath) {
    return new Promise((resolve, reject) => {
      const sql = `INSERT INTO jobs (job_id, output_path) VALUES (?, ?)`;
      
      this.db.run(sql, [jobId, outputPath], function(err) {
        if (err) {
          reject(err);
        } else {
          resolve(true);
        }
      });
    });
  }

  // Get job by ID
  getJob(jobId) {
    return new Promise((resolve, reject) => {
      const sql = `SELECT * FROM jobs WHERE job_id = ?`;
      
      this.db.get(sql, [jobId], (err, row) => {
        if (err) {
          reject(err);
        } else {
          resolve(row);
        }
      });
    });
  }

  // Get all jobs
  getAllJobs() {
    return new Promise((resolve, reject) => {
      const sql = `SELECT * FROM jobs ORDER BY created_at DESC`;
      
      this.db.all(sql, [], (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  // Delete job
  deleteJob(jobId) {
    return new Promise((resolve, reject) => {
      const sql = `DELETE FROM jobs WHERE job_id = ?`;
      
      this.db.run(sql, [jobId], function(err) {
        if (err) {
          reject(err);
        } else {
          resolve(this.changes);
        }
      });
    });
  }

  // Delete job
  // Delete ALL jobs from database
  deleteAllJobs() {
      return new Promise((resolve, reject) => {
          const sql = `DELETE FROM jobs`;
          
          this.db.run(sql, function(err) {
              if (err) {
                  reject(err);
              } else {
                  resolve(this.changes); // Returns number of deleted rows
              }
          });
      });
  }

  // Close database connection
  close() {
    if (this.db) {
      this.db.close((err) => {
        if (err) {
          console.error('Error closing database:', err.message);
        } else {
          console.log('Database connection closed.');
        }
      });
    }
  }
}

// Create a singleton instance
module.exports = new Database();