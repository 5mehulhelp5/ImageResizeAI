# Genaker ImageBundle - Magento Module

Magento 2 module for intelligent image resizing with caching and AI-powered image modification support.

## Features

- **Image Resizing**: Resize images with width, height, quality, and format parameters
- **URL-based Resizing**: Resize images via URL parameters (e.g., `/media/resize/index/imagePath/image.jpg?w=100&h=100&f=webp`)
- **Caching**: Automatic caching of resized images for performance
- **Signature Validation**: Optional signature-based URL validation for security
- **Admin Panel**: Admin interface for generating resize URLs
- **Configuration**: System configuration for limits, formats, and API keys

## Installation

1. Copy the module to `app/code/Genaker/ImageBundle`
2. Run `bin/magento module:enable Genaker_ImageBundle`
3. Run `bin/magento setup:upgrade`
4. Run `bin/magento cache:flush`

## Configuration

Navigate to **Stores > Configuration > Genaker > Image Resize** to configure:

- Signature validation
- Signature salt
- Regular URL format
- Gemini API key (for AI image modification)
- Lock retry count
- File manager cache

## Usage

### Frontend URL Format

```
/media/resize/index/imagePath/{image_path}?w={width}&h={height}&f={format}&q={quality}
```

Example:
```
/media/resize/index/imagePath/catalog/product/image.jpg?w=300&h=300&f=webp&q=85
```

### With Signature (if enabled)

```
/media/resize/index/imagePath/{image_path}?w={width}&h={height}&f={format}&sig={signature}
```

### Admin URL Generator

Navigate to **Genaker > Image Resize > Generate** to generate resize URLs with signature.

## Parameters

- `w` - Width (pixels)
- `h` - Height (pixels)
- `q` - Quality (0-100)
- `f` - Format (webp, jpg, jpeg, png, gif) - **Required**
- `sig` - Signature (if signature validation is enabled)

## Requirements

- Magento 2.4.x
- PHP 7.4+

## License

Copyright (c) 2024 Genaker

