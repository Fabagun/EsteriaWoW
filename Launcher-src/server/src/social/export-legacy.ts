import { Store } from './store.js';
const store = new Store(process.env.SOCIAL_DATA_DIR ?? './social-data');
try { await store.load(); await store.exportLegacy(); console.log('Legacy social snapshots exported. Keep the SQLite database as the rollback backup.'); }
finally { store.close(); }
