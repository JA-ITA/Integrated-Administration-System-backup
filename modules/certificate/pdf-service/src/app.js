/**
 * ITADIAS Certificate PDF Generation Service
 * Uses Handlebars templates and PDF-lib for certificate generation
 */

const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs-extra');
const { PDFDocument, StandardFonts, rgb } = require('pdf-lib');
const Handlebars = require('handlebars');
const fontkit = require('@pdf-lib/fontkit');
const winston = require('winston');
const rateLimit = require('express-rate-limit');
const { v4: uuidv4 } = require('uuid');

// Configure logging
const logger = winston.createLogger({
    level: process.env.LOG_LEVEL || 'info',
    format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.errors({ stack: true }),
        winston.format.json()
    ),
    transports: [
        new winston.transports.Console({
            format: winston.format.simple()
        })
    ]
});

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(bodyParser.json({ limit: '50mb' }));
app.use(bodyParser.urlencoded({ extended: true, limit: '50mb' }));

// Rate limiting
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100, // Limit each IP to 100 requests per windowMs
    message: 'Too many PDF generation requests from this IP',
    standardHeaders: true,
    legacyHeaders: false,
});

app.use('/generate-pdf', limiter);

// Caching
const templateCache = new Map();
const fontCache = new Map();

// Register Handlebars helpers
Handlebars.registerHelper('formatDate', function(date) {
    try {
        const d = new Date(date);
        return d.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    } catch (e) {
        return date;
    }
});

Handlebars.registerHelper('uppercase', function(str) {
    return typeof str === 'string' ? str.toUpperCase() : str;
});

Handlebars.registerHelper('eq', function(a, b) {
    return a === b;
});

Handlebars.registerHelper('formatExpiryDate', function(date) {
    if (!date) return 'Does Not Expire';
    try {
        const d = new Date(date);
        return d.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    } catch (e) {
        return 'Invalid Date';
    }
});

// Helper functions
async function loadTemplate(templateName) {
    if (templateCache.has(templateName)) {
        return templateCache.get(templateName);
    }
    
    try {
        const templatePath = path.join(__dirname, '../templates', `${templateName}.hbs`);
        const templateContent = await fs.readFile(templatePath, 'utf8');
        const compiledTemplate = Handlebars.compile(templateContent);
        
        templateCache.set(templateName, compiledTemplate);
        logger.info(`Template loaded and cached: ${templateName}`);
        return compiledTemplate;
    } catch (error) {
        logger.error(`Failed to load template: ${templateName}`, { error: error.message });
        throw new Error(`Template not found: ${templateName}`);
    }
}

async function loadFont(fontPath) {
    if (fontCache.has(fontPath)) {
        return fontCache.get(fontPath);
    }
    
    try {
        const fontBytes = await fs.readFile(fontPath);
        fontCache.set(fontPath, fontBytes);
        logger.info(`Font loaded and cached: ${fontPath}`);
        return fontBytes;
    } catch (error) {
        logger.error(`Failed to load font: ${fontPath}`, { error: error.message });
        throw new Error(`Font not found: ${fontPath}`);
    }
}

function parseHTMLForPDF(htmlContent) {
    const elements = [];
    
    // Extract certificate elements based on CSS classes and structure
    // This is a simplified parser - in production you might use a proper HTML parser
    
    // Extract title
    const titleMatch = htmlContent.match(/<div[^>]*class="certificate-title"[^>]*>(.*?)<\/div>/s);
    if (titleMatch) {
        const title = titleMatch[1].replace(/<[^>]*>/g, '').trim();
        elements.push({
            type: 'title',
            text: title,
            fontSize: 28,
            fontWeight: 'bold',
            color: [0, 0.42, 0.33], // ITADIAS green #006B54
            alignment: 'center',
            marginBottom: 30
        });
    }
    
    // Extract recipient name
    const nameMatch = htmlContent.match(/<div[^>]*class="recipient-name"[^>]*>(.*?)<\/div>/s);
    if (nameMatch) {
        const name = nameMatch[1].replace(/<[^>]*>/g, '').trim();
        elements.push({
            type: 'name',
            text: name,
            fontSize: 24,
            fontWeight: 'bold',
            alignment: 'center',
            marginBottom: 20
        });
    }
    
    // Extract certificate content
    const contentMatch = htmlContent.match(/<div[^>]*class="certificate-content"[^>]*>(.*?)<\/div>/s);
    if (contentMatch) {
        const content = contentMatch[1].replace(/<[^>]*>/g, '').trim();
        elements.push({
            type: 'content',
            text: content,
            fontSize: 14,
            alignment: 'center',
            marginBottom: 30
        });
    }
    
    // Extract details table
    const detailsMatch = htmlContent.match(/<table[^>]*class="certificate-details"[^>]*>(.*?)<\/table>/s);
    if (detailsMatch) {
        const rows = detailsMatch[1].match(/<tr[^>]*>(.*?)<\/tr>/gs) || [];
        
        rows.forEach(row => {
            const cells = row.match(/<td[^>]*>(.*?)<\/td>/gs) || [];
            if (cells.length >= 2) {
                const label = cells[0].replace(/<[^>]*>/g, '').trim();
                const value = cells[1].replace(/<[^>]*>/g, '').trim();
                
                elements.push({
                    type: 'detail',
                    label: label,
                    value: value,
                    fontSize: 12,
                    marginBottom: 8
                });
            }
        });
    }
    
    return elements;
}

async function renderContentToPDF(page, elements, fonts, options) {
    const { width, height } = page.getSize();
    let currentY = height - 80; // Start from top with margin
    
    // Add ITADIAS logo/header if available
    currentY -= 40;
    
    // Render title
    page.drawText('Island Traffic Authority', {
        x: (width - fonts.helveticaBold.widthOfTextAtSize('Island Traffic Authority', 16)) / 2,
        y: currentY,
        size: 16,
        font: fonts.helveticaBold,
        color: rgb(0, 0.42, 0.33)
    });
    currentY -= 30;
    
    for (const element of elements) {
        const font = element.fontWeight === 'bold' ? fonts.helveticaBold : fonts.helvetica;
        const fontSize = element.fontSize || 12;
        
        if (element.type === 'title') {
            const textWidth = font.widthOfTextAtSize(element.text, fontSize);
            const x = (width - textWidth) / 2;
            
            page.drawText(element.text, {
                x: x,
                y: currentY,
                size: fontSize,
                font: font,
                color: rgb(element.color[0], element.color[1], element.color[2])
            });
            
            // Add underline
            page.drawLine({
                start: { x: x, y: currentY - 5 },
                end: { x: x + textWidth, y: currentY - 5 },
                thickness: 2,
                color: rgb(element.color[0], element.color[1], element.color[2])
            });
            
        } else if (element.type === 'name') {
            const textWidth = font.widthOfTextAtSize(element.text, fontSize);
            const x = (width - textWidth) / 2;
            
            page.drawText(element.text, {
                x: x,
                y: currentY,
                size: fontSize,
                font: font,
                color: rgb(0, 0, 0)
            });
            
        } else if (element.type === 'content') {
            // Split long content into multiple lines
            const maxWidth = width - 100;
            const words = element.text.split(' ');
            let currentLine = '';
            
            for (const word of words) {
                const testLine = currentLine + (currentLine ? ' ' : '') + word;
                const testWidth = font.widthOfTextAtSize(testLine, fontSize);
                
                if (testWidth > maxWidth && currentLine) {
                    // Draw current line
                    const lineWidth = font.widthOfTextAtSize(currentLine, fontSize);
                    const x = (width - lineWidth) / 2;
                    
                    page.drawText(currentLine, {
                        x: x,
                        y: currentY,
                        size: fontSize,
                        font: font,
                        color: rgb(0, 0, 0)
                    });
                    
                    currentY -= fontSize + 5;
                    currentLine = word;
                } else {
                    currentLine = testLine;
                }
            }
            
            // Draw remaining line
            if (currentLine) {
                const lineWidth = font.widthOfTextAtSize(currentLine, fontSize);
                const x = (width - lineWidth) / 2;
                
                page.drawText(currentLine, {
                    x: x,
                    y: currentY,
                    size: fontSize,
                    font: font,
                    color: rgb(0, 0, 0)
                });
            }
            
        } else if (element.type === 'detail') {
            // Two-column layout for details
            const leftX = 100;
            const rightX = 350;
            
            // Label
            page.drawText(element.label + ':', {
                x: leftX,
                y: currentY,
                size: fontSize,
                font: fonts.helveticaBold,
                color: rgb(0, 0, 0)
            });
            
            // Value
            page.drawText(element.value, {
                x: rightX,
                y: currentY,
                size: fontSize,
                font: fonts.helvetica,
                color: rgb(0, 0, 0)
            });
        }
        
        currentY -= (element.marginBottom || 15);
        
        // Add new page if needed
        if (currentY < 100) {
            const newPage = page.doc.addPage([595, 842]);
            currentY = height - 80;
        }
    }
    
    // Add QR code if provided
    if (options.qrCodeImage) {
        try {
            // QR code would be embedded here if image data is provided
            const qrSize = 80;
            const qrX = width - qrSize - 50;
            const qrY = 50;
            
            // Placeholder for QR code - in real implementation, embed the QR image
            page.drawRectangle({
                x: qrX,
                y: qrY,
                width: qrSize,
                height: qrSize,
                borderColor: rgb(0, 0, 0),
                borderWidth: 1
            });
            
            page.drawText('QR Code', {
                x: qrX + 15,
                y: qrY + 35,
                size: 10,
                font: fonts.helvetica,
                color: rgb(0.5, 0.5, 0.5)
            });
        } catch (e) {
            logger.warn('Failed to add QR code to PDF', { error: e.message });
        }
    }
    
    // Add footer with certificate ID and date
    const footerY = 30;
    page.drawText(`Certificate ID: ${options.certificateId || 'N/A'}`, {
        x: 50,
        y: footerY,
        size: 8,
        font: fonts.helvetica,
        color: rgb(0.5, 0.5, 0.5)
    });
    
    const dateText = `Generated: ${new Date().toLocaleDateString()}`;
    const dateWidth = fonts.helvetica.widthOfTextAtSize(dateText, 8);
    page.drawText(dateText, {
        x: width - dateWidth - 50,
        y: footerY,
        size: 8,
        font: fonts.helvetica,
        color: rgb(0.5, 0.5, 0.5)
    });
}

// Routes
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'Certificate PDF Generation Service',
        version: '1.0.0',
        timestamp: new Date().toISOString()
    });
});

app.post('/generate-pdf', async (req, res) => {
    const startTime = Date.now();
    const requestId = uuidv4();
    
    logger.info('PDF generation started', {
        requestId,
        templateName: req.body.templateName
    });
    
    try {
        const { templateName, context, options = {} } = req.body;
        
        // Input validation
        if (!templateName || !context) {
            const error = 'Template name and context are required';
            logger.warn(error, { requestId });
            return res.status(400).json({ error });
        }
        
        // Load template
        const template = await loadTemplate(templateName);
        const htmlContent = template(context);
        
        // Create PDF document
        const pdfDoc = await PDFDocument.create();
        pdfDoc.registerFontkit(fontkit);
        
        // Load fonts
        const fonts = {
            helvetica: await pdfDoc.embedFont(StandardFonts.Helvetica),
            helveticaBold: await pdfDoc.embedFont(StandardFonts.HelveticaBold)
        };
        
        // Add page (A4 portrait)
        const page = pdfDoc.addPage([595, 842]);
        
        // Parse HTML content
        const parsedContent = parseHTMLForPDF(htmlContent);
        
        // Render content to PDF
        await renderContentToPDF(page, parsedContent, fonts, {
            ...options,
            certificateId: context.certificateId,
            qrCodeImage: context.qrCodeImage
        });
        
        // Generate PDF bytes
        const pdfBytes = await pdfDoc.save();
        
        const processingTime = Date.now() - startTime;
        logger.info('PDF generation completed', {
            requestId,
            processingTime,
            pdfSize: pdfBytes.length
        });
        
        // Return response
        if (options.returnFormat === 'base64') {
            res.json({
                success: true,
                data: {
                    pdf: Buffer.from(pdfBytes).toString('base64'),
                    metadata: {
                        size: pdfBytes.length,
                        processingTime,
                        requestId
                    }
                }
            });
        } else {
            res.set({
                'Content-Type': 'application/pdf',
                'Content-Length': pdfBytes.length,
                'Content-Disposition': `attachment; filename="${templateName}-${requestId}.pdf"`
            });
            res.send(Buffer.from(pdfBytes));
        }
        
    } catch (error) {
        const processingTime = Date.now() - startTime;
        logger.error('PDF generation failed', {
            requestId,
            processingTime,
            error: error.message,
            stack: error.stack
        });
        
        res.status(500).json({
            error: 'PDF generation failed',
            message: error.message,
            requestId
        });
    }
});

// Error handling middleware
app.use((error, req, res, next) => {
    logger.error('Unhandled error', { error: error.message, stack: error.stack });
    res.status(500).json({ error: 'Internal server error' });
});

// Start server
app.listen(PORT, () => {
    logger.info(`PDF service running on port ${PORT}`);
});

module.exports = app;