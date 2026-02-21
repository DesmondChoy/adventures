/**
 * Module version helper for dynamic imports.
 * Ensures dynamic imports use the same cache-busting version as the caller module.
 */

export function withCurrentModuleVersion(importMetaUrl, modulePath) {
    const version = new URL(importMetaUrl).searchParams.get('v');
    if (!version) {
        return modulePath;
    }

    const separator = modulePath.includes('?') ? '&' : '?';
    return `${modulePath}${separator}v=${version}`;
}
