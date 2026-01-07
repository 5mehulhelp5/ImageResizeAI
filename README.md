# Genaker ImageAIBundle - Magento 2 Module

Magento 2 module for intelligent image resizing with caching and AI-powered image modification support. This module provides on-the-fly image resizing with support for multiple formats, quality control, and optional AI-powered image enhancement using Google Gemini API.

## Features

- **On-the-Fly Image Resizing**: Resize images dynamically via URL parameters
- **Multiple Format Support**: WebP, JPEG, PNG, GIF support with automatic format conversion
- **Intelligent Caching**: Automatic caching of resized images for optimal performance
- **Signature Validation**: Optional signature-based URL validation for security
- **AI-Powered Enhancement**: Integration with Google Gemini API for AI image modification (optional)
- **Admin Panel**: Admin interface for generating resize URLs with signatures
- **Configurable Limits**: System configuration for width, height, quality limits
- **Performance Optimized**: Efficient caching and file management

## Installation

### Via Composer (Recommended)

```bash
composer require genaker/imageaibundle
bin/magento module:enable Genaker_ImageAIBundle
bin/magento setup:upgrade
bin/magento cache:flush
```

### Manual Installation

1. Copy the module to `app/code/Genaker/ImageAIBundle`
2. Run the following commands:
```bash
bin/magento module:enable Genaker_ImageAIBundle
bin/magento setup:upgrade
bin/magento cache:flush
```

## Configuration

Navigate to **Stores > Configuration > Genaker > Image AI Resize** to configure:

### General Settings

- **Enable Signature Validation**: Enable signature validation for image resize URLs (recommended for production)
- **Signature Salt**: Secret salt for generating image resize URL signatures (required if signature validation is enabled)
- **Enable Regular URL Format**: Allow query string format URLs (e.g., `?w=100&h=100`)
- **Gemini API Key**: Google Gemini API key for AI image modification (optional)
- **Lock Retry Count**: Number of retries when acquiring lock for image processing (default: 3)
- **Use File Manager for Cache**: Use Magento file manager for cache tracking

### Default Limits

- **Width**: 20-5000 pixels
- **Height**: 20-5000 pixels
- **Quality**: 0-100
- **Allowed Formats**: webp, jpg, jpeg, png, gif
- **Allowed Aspect Ratios**: inset, outbound

## Usage

### Frontend URL Format

#### Basic Resize
```
/media/resize/index/imagePath/{image_path}?w={width}&h={height}&f={format}&q={quality}
```

**Example:**
```
/media/resize/index/imagePath/catalog/product/image.jpg?w=300&h=300&f=webp&q=85
```

#### With Signature (if enabled)
```
/media/resize/index/imagePath/{image_path}?w={width}&h={height}&f={format}&sig={signature}
```

### URL Parameters

| Parameter | Description | Required | Example |
|-----------|-------------|----------|---------|
| `w` | Width in pixels | No | `300` |
| `h` | Height in pixels | No | `300` |
| `q` | Quality (0-100) | No | `85` |
| `f` | Format (webp, jpg, jpeg, png, gif) | **Yes** | `webp` |
| `a` | Aspect ratio (inset, outbound) | No | `inset` |
| `sig` | Signature (if validation enabled) | Yes* | `abc123...` |
| `prompt` | AI modification prompt (admin only) | No | `enhance colors` |

\* Required only if signature validation is enabled

### Admin URL Generator

Navigate to **Genaker > Image Resize > Generate** to generate resize URLs with signature validation.

## API Usage

### Service Interface

```php
use Genaker\ImageAIBundle\Api\ImageResizeServiceInterface;

class YourClass
{
    private ImageResizeServiceInterface $imageResizeService;
    
    public function __construct(ImageResizeServiceInterface $imageResizeService)
    {
        $this->imageResizeService = $imageResizeService;
    }
    
    public function resizeImage()
    {
        $params = [
            'w' => 300,
            'h' => 300,
            'f' => 'webp',
            'q' => 85
        ];
        
        $result = $this->imageResizeService->resizeImage(
            'catalog/product/image.jpg',
            $params
        );
        
        // Access result properties
        $filePath = $result->getFilePath();
        $mimeType = $result->getMimeType();
        $fromCache = $result->isFromCache();
    }
}
```

## Cache Management

Resized images are automatically cached in `/pub/media/cache/resize/` directory. The cache structure follows the image path structure for easy management.

### Clearing Cache

To clear all resized image cache:
```bash
rm -rf pub/media/cache/resize/*
```

Or use Magento cache management:
```bash
bin/magento cache:clean
```

## Security

### Signature Validation

When signature validation is enabled, all resize URLs must include a valid signature parameter. This prevents unauthorized image resizing and protects against abuse.

**Generating Signatures:**

The signature is calculated as:
```php
$signature = md5($imagePath . '|' . $sortedParams . '|' . $salt);
```

Where:
- `$imagePath` is the image path
- `$sortedParams` is URL-encoded query string of sorted parameters
- `$salt` is the configured signature salt

## Performance

- **Caching**: All resized images are cached to disk for fast subsequent requests
- **Lazy Processing**: Images are only processed when requested
- **Optimized Formats**: WebP support for smaller file sizes
- **Lock Mechanism**: Prevents race conditions during concurrent requests

## Requirements

- **Magento**: 2.4.x
- **PHP**: 7.4 or higher
- **Extensions**: GD or Imagick (for image processing)
- **Optional**: Google Gemini API key (for AI features)

## Troubleshooting

### Images Not Resizing

1. Check file permissions on `/pub/media/cache/resize/`
2. Verify image path is correct
3. Check Magento logs: `var/log/system.log`
4. Ensure format parameter (`f`) is provided

### Signature Validation Failing

1. Verify signature salt is configured correctly
2. Ensure parameters are sorted alphabetically when generating signature
3. Check that signature parameter is included in URL

### Cache Not Working

1. Verify directory permissions: `chmod -R 755 pub/media/cache/`
2. Check disk space availability
3. Verify Magento cache is enabled

## Development

### Module Structure

```
app/code/Genaker/ImageAIBundle/
├── Api/
│   └── ImageResizeServiceInterface.php
├── Controller/
│   ├── Resize/
│   │   └── Index.php
│   └── Adminhtml/
│       └── Generate/
│           └── Index.php
├── Model/
│   └── ResizeResult.php
├── Service/
│   └── ImageResizeService.php
└── etc/
    ├── module.xml
    ├── config.xml
    ├── system.xml
    ├── di.xml
    ├── acl.xml
    ├── frontend/
    │   └── routes.xml
    └── adminhtml/
        └── routes.xml
```

## License

Copyright (c) 2024 Genaker. All rights reserved.

## Support

For issues, questions, or contributions, please visit: https://github.com/Genaker/ImageResizeAI

## Changelog

### Version 1.0.0
- Initial release
- Basic image resizing functionality
- Signature validation support
- Admin URL generator
- Multiple format support
- Caching system
