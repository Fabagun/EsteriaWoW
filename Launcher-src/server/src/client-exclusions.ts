/** Runtime files are never part of client delivery, at any directory depth. */
export const isExcludedClientPath = (relativePath: string): boolean => {
	const parts = relativePath.replace(/\\/g, '/').toLowerCase().split('/');
	return parts.some(part => part === 'logs' || part === 'errors' || part === 'cache') ||
		parts.at(-1)!.endsWith('.log');
};
