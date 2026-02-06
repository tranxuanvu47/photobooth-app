# Wedding Photo Booth - Print Agent

This is a local Node.js server that enables direct printing from the Wedding Photo Booth application without requiring browser print dialogs.

## Features

- Direct printing to system printers
- Support for Windows, macOS, and Linux
- Multiple copies support
- Printer selection
- CORS enabled for local development

## Installation

1. Navigate to the print-agent directory:
```bash
cd print-agent
```

2. Install dependencies:
```bash
npm install
```

## Usage

### Starting the Print Agent

Run the print agent server:
```bash
npm start
```

The server will start on `http://localhost:3000`

For development with auto-reload:
```bash
npm run dev
```

### Endpoints

#### GET /status
Returns server status and available printers
```json
{
  "available": true,
  "version": "1.0.0",
  "printers": ["Printer 1", "Printer 2"]
}
```

#### POST /print
Prints an image file
- Body: multipart/form-data
- Fields:
  - `image`: Image file (required)
  - `copies`: Number of copies (default: 1)
  - `paperSize`: Paper size - "4x6" or "2x6" (default: "4x6")
  - `orientation`: "portrait" or "landscape" (default: "portrait")
  - `printer`: Printer name (optional, uses default if not specified)

## Canon Selphy CP Setup

### Windows Setup for Canon Selphy CP

1. **Install Canon Selphy CP Driver**
   - Download and install the official Canon Selphy CP driver from Canon website
   - Make sure the printer is properly connected and recognized by Windows

2. **Configure Printer Settings**
   - Open Windows Settings > Devices > Printers & scanners
   - Find your Canon Selphy CP printer
   - Click "Manage" > "Printing preferences"
   - Set Paper Size to **4x6 inches** (or 100x150mm)
   - Set Paper Type to **Photo Paper**
   - Save settings

3. **Set as Default Printer (Optional)**
   - Right-click Canon Selphy CP printer
   - Select "Set as default printer"

4. **Using Print Agent**
   - Start the print agent: `npm start`
   - In the web app, select "Direct Print (Agent)" method
   - Select "Canon Selphy CP" from the printer dropdown
   - Choose paper size: **4x6 inches**
   - Click "Print with Agent"

### Browser Print Method (Alternative)

If print agent doesn't work, use browser print:

1. Click "Print with Browser"
2. In the print dialog:
   - **Select Canon Selphy CP** as the printer
   - Click "More settings" or "Printer properties"
   - Set Paper Size to **4x6 inches** (or 100x150mm)
   - Set Paper Type to **Photo Paper**
   - Uncheck "Fit to page" if you want exact size
   - Click Print

### Troubleshooting Canon Selphy CP

- **Prints as A4 instead of 4x6**: 
  - Make sure printer properties are set to 4x6 inches
  - Use "Direct Print (Agent)" method instead of browser print
  - Check printer driver settings in Windows

- **Printer not found**:
  - Verify printer is connected and powered on
  - Check Windows can see the printer in Settings
  - Restart print agent after connecting printer

- **Print quality issues**:
  - Ensure using Photo Paper setting
  - Check printer has ink/paper
  - Verify image resolution is sufficient (300 DPI recommended)

## Platform-Specific Notes

### Windows
- Uses `rundll32.exe` for printing
- Requires image viewer (shimgvw.dll)
- For Canon Selphy CP: Configure printer properties to use 4x6 paper size
- Alternative: Install `node-printer` package for better Windows support

### macOS / Linux
- Uses `lpr` command with paper size options
- Requires CUPS printing system
- Printers must be configured in system settings
- For Canon Selphy CP: Use `-o media=Custom.4x6in` option

## Security Considerations

⚠️ **Important Security Notes:**

1. This server should ONLY run on trusted local networks
2. It has CORS enabled for all origins (development only)
3. For production, implement proper authentication
4. Restrict access to localhost or specific IPs
5. Consider adding rate limiting

## Troubleshooting

### No printers found
- Verify printers are installed and configured in system settings
- Check printer is powered on and connected
- Run system printer test page

### Print fails
- Check printer queue for errors
- Verify file format is supported
- Check printer has paper and ink
- Review console logs for detailed errors

### Port already in use
- Change PORT constant in server.js
- Update Angular app to match new port

## Production Recommendations

For production use, consider:

1. **Better printing library**: Use `node-printer` or `pdf-to-printer` for more reliable printing
2. **Authentication**: Add API key or token authentication
3. **HTTPS**: Use SSL certificates for secure communication
4. **Logging**: Implement proper logging system
5. **Error handling**: Enhanced error reporting and recovery
6. **Queue system**: Implement print queue for high-volume scenarios

## Alternative Solutions

If the print agent doesn't meet your needs:

1. **Cloud printing**: Use Google Cloud Print API (deprecated) or alternative services
2. **PDF generation**: Generate PDFs and let users print via browser
3. **Email**: Send high-res images via email for printing
4. **Third-party services**: Use dedicated photo printing services with API

## License

MIT

