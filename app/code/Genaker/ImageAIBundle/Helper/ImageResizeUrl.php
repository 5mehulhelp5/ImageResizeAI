<?php
/**
 * Genaker ImageAIBundle
 *
 * @category    Genaker
 * @package     Genaker_ImageAIBundle
 * @author      Genaker
 * @copyright   Copyright (c) 2024 Genaker
 */

namespace Genaker\ImageAIBundle\Helper;

use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Framework\UrlInterface;

/**
 * Image Resize URL Helper
 * Generates image resize URLs in both base64 and regular formats
 */
class ImageResizeUrl
{
    private ScopeConfigInterface $scopeConfig;
    private UrlInterface $urlBuilder;

    public function __construct(
        ScopeConfigInterface $scopeConfig,
        UrlInterface $urlBuilder
    ) {
        $this->scopeConfig = $scopeConfig;
        $this->urlBuilder = $urlBuilder;
    }

    /**
     * Generate image resize URL
     *
     * @param string $imagePath Image path
     * @param array $params Resize parameters
     * @param bool $base64Format Use base64 format (true) or query string format (false)
     * @return string Generated URL
     */
    public function generateImageResizeUrl(string $imagePath, array $params, bool $base64Format = false): string
    {
        if ($base64Format) {
            return $this->generateBase64Url($imagePath, $params);
        } else {
            return $this->generateRegularUrl($imagePath, $params);
        }
    }

    /**
     * Generate base64 encoded URL format: /media/resize/{base64}.{extension}
     *
     * @param string $imagePath
     * @param array $params
     * @return string
     */
    private function generateBase64Url(string $imagePath, array $params): string
    {
        // Ensure image path starts with /
        if (!str_starts_with($imagePath, '/')) {
            $imagePath = '/' . $imagePath;
        }

        // Prepare parameters for encoding
        $encodeParams = $params;
        
        // Add image path to params
        $encodeParams['image'] = $imagePath;
        
        // Generate signature if enabled
        $signatureEnabled = $this->isSignatureEnabled();
        if ($signatureEnabled) {
            $salt = $this->getSignatureSalt();
            if (!empty($salt)) {
                // Generate signature (without 'image' and 'sig' in params)
                $signatureParams = $params;
                $signature = $this->generateSignature($imagePath, $signatureParams, $salt);
                $encodeParams['sig'] = $signature;
            }
        }

        // Sort parameters alphabetically for consistent encoding
        ksort($encodeParams);
        
        // Build query string
        $queryString = http_build_query($encodeParams);
        
        // Encode to base64 (URL-safe)
        $base64String = base64_encode($queryString);
        // Convert to URL-safe base64 (replace + with -, / with _)
        $base64String = strtr($base64String, '+/', '-_');
        // Remove padding
        $base64String = rtrim($base64String, '=');
        
        // Get format from params or infer from image path
        $format = $params['f'] ?? $this->getFormatFromPath($imagePath);
        
        // Build URL: /media/resize/{base64}.{extension}
        return '/media/resize/index/imagePath/' . $base64String . '.' . $format;
    }

    /**
     * Generate regular query string URL format
     *
     * @param string $imagePath
     * @param array $params
     * @return string
     */
    private function generateRegularUrl(string $imagePath, array $params): string
    {
        // Ensure image path starts with /
        if (!str_starts_with($imagePath, '/')) {
            $imagePath = '/' . $imagePath;
        }

        // Build query parameters
        $queryParams = $params;
        
        // Generate signature if enabled
        $signatureEnabled = $this->isSignatureEnabled();
        if ($signatureEnabled) {
            $salt = $this->getSignatureSalt();
            if (!empty($salt)) {
                $signature = $this->generateSignature($imagePath, $params, $salt);
                $queryParams['sig'] = $signature;
            }
        }

        // Build URL with query string
        $url = $this->urlBuilder->getUrl('media/resize/index', ['imagePath' => ltrim($imagePath, '/')]);
        $url .= '?' . http_build_query($queryParams);
        
        return $url;
    }

    /**
     * Generate signature
     *
     * @param string $imagePath
     * @param array $params
     * @param string $salt
     * @return string
     */
    private function generateSignature(string $imagePath, array $params, string $salt): string
    {
        $filteredParams = array_filter($params, fn($value) => $value !== null);
        ksort($filteredParams);
        $paramString = http_build_query($filteredParams);
        $signatureString = $imagePath . '|' . $paramString . '|' . $salt;
        return md5($signatureString);
    }

    /**
     * Check if signature validation is enabled
     *
     * @return bool
     */
    private function isSignatureEnabled(): bool
    {
        return (bool)$this->scopeConfig->getValue(
            'genaker_imageaibundle/general/signature_enabled',
            \Magento\Store\Model\ScopeInterface::SCOPE_STORE
        );
    }

    /**
     * Get signature salt
     *
     * @return string
     */
    private function getSignatureSalt(): string
    {
        $salt = $this->scopeConfig->getValue(
            'genaker_imageaibundle/general/signature_salt',
            \Magento\Store\Model\ScopeInterface::SCOPE_STORE
        );

        // Decrypt if encrypted
        if ($salt && class_exists('\Magento\Framework\Encryption\EncryptorInterface')) {
            $encryptor = \Magento\Framework\App\ObjectManager::getInstance()
                ->get(\Magento\Framework\Encryption\EncryptorInterface::class);
            $salt = $encryptor->decrypt($salt);
        }

        return $salt ?: '';
    }

    /**
     * Get format from image path
     *
     * @param string $imagePath
     * @return string
     */
    private function getFormatFromPath(string $imagePath): string
    {
        $extension = strtolower(pathinfo($imagePath, PATHINFO_EXTENSION));
        if ($extension === 'jpg') {
            return 'jpeg';
        }
        return $extension ?: 'jpg';
    }
}

