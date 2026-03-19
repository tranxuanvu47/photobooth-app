const express = require('express');
const multer = require('multer');
const fs = require('fs').promises;
const path = require('path');
const { exec } = require('child_process');
const { promisify } = require('util');

const execAsync = promisify(exec);

const app = express();
const PORT = 3000;

// Configure multer for file uploads
const storage = multer.memoryStorage();
const upload = multer({ 
  storage,
  limits: { fileSize: 50 * 1024 * 1024 } // 50MB max
});

// Enable CORS for local development
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

app.use(express.json());

// Temporary directory for print files
const TEMP_DIR = path.join(__dirname, 'temp');

// Ensure temp directory exists
(async () => {
  try {
    await fs.mkdir(TEMP_DIR, { recursive: true });
  } catch (err) {
    console.error('Failed to create temp directory:', err);
  }
})();

/**
 * Get list of available printers
 */
async function getAvailablePrinters() {
  try {
    const platform = process.platform;
    
    if (platform === 'win32') {
      // Windows: Use PowerShell
      const { stdout } = await execAsync('powershell Get-Printer | Select-Object Name | ConvertTo-Json');
      const printers = JSON.parse(stdout);
      return Array.isArray(printers) 
        ? printers.map(p => p.Name) 
        : [printers.Name];
    } else if (platform === 'darwin') {
      // macOS: Use lpstat
      const { stdout } = await execAsync('lpstat -p | awk \'{print $2}\'');
      return stdout.trim().split('\n').filter(Boolean);
    } else {
      // Linux: Use lpstat
      const { stdout } = await execAsync('lpstat -p | awk \'{print $2}\'');
      return stdout.trim().split('\n').filter(Boolean);
    }
  } catch (err) {
    console.error('Failed to get printers:', err);
    return [];
  }
}

/**
 * Print file using system printer with proper paper size settings
 */
async function printFile(filePath, printerName, copies = 1, paperSize = '4x6', orientation = 'portrait') {
  const platform = process.platform;
  
  try {
    if (platform === 'win32') {
      // Windows: Use rundll32 for printing
      // Note: Paper size should be configured in printer properties beforehand
      // For Canon Selphy CP, ensure printer is set to 4x6 inches in Windows settings
      const command = printerName 
        ? `rundll32.exe C:\\WINDOWS\\system32\\shimgvw.dll,ImageView_PrintTo /pt "${filePath}" "${printerName}"`
        : `rundll32.exe C:\\WINDOWS\\system32\\shimgvw.dll,ImageView_PrintTo /pt "${filePath}"`;
      
      console.log(`Printing to: ${printerName || 'Default Printer'}`);
      console.log(`Paper Size: ${paperSize}, Orientation: ${orientation}`);
      console.log(`Copies: ${copies}`);
      
      for (let i = 0; i < copies; i++) {
        await execAsync(command);
        // Small delay between copies to prevent queue issues
        if (i < copies - 1) {
          await new Promise(resolve => setTimeout(resolve, 800));
        }
      }
    } else if (platform === 'darwin') {
      // macOS: Use lpr with paper size options
      const printerArg = printerName ? `-P "${printerName}"` : '';
      // Canon Selphy CP typically uses 4x6 paper
      const paperSizeArg = paperSize === '4x6' ? '-o media=Custom.4x6in' : '-o media=Custom.2x6in';
      const orientationArg = orientation === 'landscape' ? '-o landscape' : '-o portrait';
      const command = `lpr ${printerArg} ${paperSizeArg} ${orientationArg} -# ${copies} "${filePath}"`;
      await execAsync(command);
    } else {
      // Linux: Use lpr with paper size options
      const printerArg = printerName ? `-P "${printerName}"` : '';
      const paperSizeArg = paperSize === '4x6' ? '-o media=Custom.4x6in' : '-o media=Custom.2x6in';
      const orientationArg = orientation === 'landscape' ? '-o landscape' : '-o portrait';
      const command = `lpr ${printerArg} ${paperSizeArg} ${orientationArg} -# ${copies} "${filePath}"`;
      await execAsync(command);
    }
    
    return true;
  } catch (err) {
    console.error('Print failed:', err);
    throw err;
  }
}

/**
 * Status endpoint
 */
app.get('/status', async (req, res) => {
  try {
    const printers = await getAvailablePrinters();
    res.json({
      available: true,
      version: '1.0.0',
      printers
    });
  } catch (err) {
    res.status(500).json({
      available: false,
      error: err.message
    });
  }
});

/**
 * Print endpoint
 */
app.post('/print', upload.single('image'), async (req, res) => {
  let tempFilePath = null;
  
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'No image file provided' });
    }

    // Get print options
    const {
      copies = 1,
      paperSize = '4x6',
      orientation = 'portrait',
      printer = null
    } = req.body;

    // Save uploaded file to temp directory
    const timestamp = Date.now();
    const ext = path.extname(req.file.originalname) || '.jpg';
    tempFilePath = path.join(TEMP_DIR, `print-${timestamp}${ext}`);
    
    await fs.writeFile(tempFilePath, req.file.buffer);

    // Print the file with paper size and orientation
    await printFile(tempFilePath, printer, parseInt(copies), paperSize, orientation);

    // Clean up after a delay (give time for print job to be sent)
    setTimeout(async () => {
      try {
        await fs.unlink(tempFilePath);
      } catch (err) {
        console.error('Failed to clean up temp file:', err);
      }
    }, 5000);

    res.json({
      success: true,
      message: 'Print job sent successfully',
      copies: parseInt(copies)
    });
  } catch (err) {
    console.error('Print error:', err);
    
    // Clean up on error
    if (tempFilePath) {
      try {
        await fs.unlink(tempFilePath);
      } catch (e) {
        // Ignore cleanup errors
      }
    }

    res.status(500).json({
      error: 'Print failed',
      message: err.message
    });
  }
});

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Start server
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════╗
║                                                        ║
║         Wedding Photo Booth - Print Agent             ║
║                                                        ║
║  Server running on http://localhost:${PORT}            ║
║                                                        ║
║  Status: http://localhost:${PORT}/status               ║
║                                                        ║
╚════════════════════════════════════════════════════════╝
  `);
  
  // Log available printers on startup
  getAvailablePrinters().then(printers => {
    if (printers.length > 0) {
      console.log('\n📷 Available Printers:');
      printers.forEach((printer, index) => {
        console.log(`   ${index + 1}. ${printer}`);
      });
      console.log('');
    } else {
      console.log('\n⚠️  No printers found. Please check your printer connections.\n');
    }
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  console.log('Shutting down print agent...');
  
  // Clean up temp directory
  try {
    const files = await fs.readdir(TEMP_DIR);
    for (const file of files) {
      await fs.unlink(path.join(TEMP_DIR, file));
    }
  } catch (err) {
    console.error('Cleanup error:', err);
  }
  
  process.exit(0);
});

