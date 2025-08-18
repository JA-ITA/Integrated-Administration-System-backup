// IndexedDB service for offline checklist storage
class ChecklistOfflineService {
  constructor() {
    this.dbName = 'ChecklistDB';
    this.version = 1;
    this.db = null;
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(this.dbName, this.version);

      request.onerror = () => {
        reject(new Error('Failed to open IndexedDB'));
      };

      request.onsuccess = (event) => {
        this.db = event.target.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Checklists store
        if (!db.objectStoreNames.contains('checklists')) {
          const checklistStore = db.createObjectStore('checklists', { keyPath: 'id' });
          checklistStore.createIndex('driver_record_id', 'driver_record_id', { unique: false });
          checklistStore.createIndex('examiner_id', 'examiner_id', { unique: false });
          checklistStore.createIndex('status', 'status', { unique: false });
          checklistStore.createIndex('test_type', 'test_type', { unique: false });
          checklistStore.createIndex('synced', 'synced', { unique: false });
        }

        // Sync queue store for changes that need to be synced
        if (!db.objectStoreNames.contains('sync_queue')) {
          const syncStore = db.createObjectStore('sync_queue', { keyPath: 'id', autoIncrement: true });
          syncStore.createIndex('checklist_id', 'checklist_id', { unique: false });
          syncStore.createIndex('action', 'action', { unique: false });
          syncStore.createIndex('timestamp', 'timestamp', { unique: false });
        }
      };
    });
  }

  async ensureDB() {
    if (!this.db) {
      await this.init();
    }
    return this.db;
  }

  // Checklist operations
  async saveChecklist(checklist) {
    const db = await this.ensureDB();
    const transaction = db.transaction(['checklists'], 'readwrite');
    const store = transaction.objectStore('checklists');
    
    return new Promise((resolve, reject) => {
      const request = store.put({
        ...checklist,
        updated_at: new Date().toISOString(),
        synced: checklist.synced !== false ? false : checklist.synced // Default to unsynced unless explicitly set
      });

      request.onsuccess = () => {
        resolve(checklist);
        this.addToSyncQueue(checklist.id, 'update', checklist);
      };

      request.onerror = () => {
        reject(new Error('Failed to save checklist to IndexedDB'));
      };
    });
  }

  async getChecklist(checklistId) {
    const db = await this.ensureDB();
    const transaction = db.transaction(['checklists'], 'readonly');
    const store = transaction.objectStore('checklists');

    return new Promise((resolve, reject) => {
      const request = store.get(checklistId);

      request.onsuccess = () => {
        resolve(request.result || null);
      };

      request.onerror = () => {
        reject(new Error('Failed to get checklist from IndexedDB'));
      };
    });
  }

  async getChecklistByDriverRecord(driverRecordId) {
    const db = await this.ensureDB();
    const transaction = db.transaction(['checklists'], 'readonly');
    const store = transaction.objectStore('checklists');
    const index = store.index('driver_record_id');

    return new Promise((resolve, reject) => {
      const request = index.get(driverRecordId);

      request.onsuccess = () => {
        resolve(request.result || null);
      };

      request.onerror = () => {
        reject(new Error('Failed to get checklist by driver record from IndexedDB'));
      };
    });
  }

  async getAllChecklists(filters = {}) {
    const db = await this.ensureDB();
    const transaction = db.transaction(['checklists'], 'readonly');
    const store = transaction.objectStore('checklists');

    return new Promise((resolve, reject) => {
      const request = store.getAll();

      request.onsuccess = () => {
        let checklists = request.result || [];

        // Apply filters
        if (filters.examiner_id) {
          checklists = checklists.filter(c => c.examiner_id === filters.examiner_id);
        }
        if (filters.status) {
          checklists = checklists.filter(c => c.status === filters.status);
        }
        if (filters.test_type) {
          checklists = checklists.filter(c => c.test_type === filters.test_type);
        }

        // Sort by updated_at descending
        checklists.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));

        resolve(checklists);
      };

      request.onerror = () => {
        reject(new Error('Failed to get all checklists from IndexedDB'));
      };
    });
  }

  async getUnsyncedChecklists() {
    const db = await this.ensureDB();
    const transaction = db.transaction(['checklists'], 'readonly');
    const store = transaction.objectStore('checklists');
    const index = store.index('synced');

    return new Promise((resolve, reject) => {
      const request = index.getAll(false);

      request.onsuccess = () => {
        resolve(request.result || []);
      };

      request.onerror = () => {
        reject(new Error('Failed to get unsynced checklists from IndexedDB'));
      };
    });
  }

  async markChecklistSynced(checklistId) {
    const checklist = await this.getChecklist(checklistId);
    if (checklist) {
      checklist.synced = true;
      await this.saveChecklist(checklist);
      await this.removeSyncQueueItem(checklistId);
    }
  }

  async deleteChecklist(checklistId) {
    const db = await this.ensureDB();
    const transaction = db.transaction(['checklists'], 'readwrite');
    const store = transaction.objectStore('checklists');

    return new Promise((resolve, reject) => {
      const request = store.delete(checklistId);

      request.onsuccess = () => {
        resolve();
        this.addToSyncQueue(checklistId, 'delete');
      };

      request.onerror = () => {
        reject(new Error('Failed to delete checklist from IndexedDB'));
      };
    });
  }

  // Sync queue operations
  async addToSyncQueue(checklistId, action, data = null) {
    const db = await this.ensureDB();
    const transaction = db.transaction(['sync_queue'], 'readwrite');
    const store = transaction.objectStore('sync_queue');

    const syncItem = {
      checklist_id: checklistId,
      action,
      data,
      timestamp: new Date().toISOString(),
      retry_count: 0
    };

    return new Promise((resolve, reject) => {
      const request = store.add(syncItem);

      request.onsuccess = () => {
        resolve(syncItem);
      };

      request.onerror = () => {
        reject(new Error('Failed to add item to sync queue'));
      };
    });
  }

  async getSyncQueue() {
    const db = await this.ensureDB();
    const transaction = db.transaction(['sync_queue'], 'readonly');
    const store = transaction.objectStore('sync_queue');

    return new Promise((resolve, reject) => {
      const request = store.getAll();

      request.onsuccess = () => {
        const items = request.result || [];
        // Sort by timestamp
        items.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        resolve(items);
      };

      request.onerror = () => {
        reject(new Error('Failed to get sync queue from IndexedDB'));
      };
    });
  }

  async removeSyncQueueItem(checklistId) {
    const db = await this.ensureDB();
    const transaction = db.transaction(['sync_queue'], 'readwrite');
    const store = transaction.objectStore('sync_queue');
    const index = store.index('checklist_id');

    return new Promise((resolve, reject) => {
      const request = index.getAllKeys(checklistId);

      request.onsuccess = () => {
        const keys = request.result;
        const deletePromises = keys.map(key => {
          return new Promise((deleteResolve) => {
            const deleteRequest = store.delete(key);
            deleteRequest.onsuccess = () => deleteResolve();
            deleteRequest.onerror = () => deleteResolve(); // Continue even if delete fails
          });
        });

        Promise.all(deletePromises).then(() => resolve());
      };

      request.onerror = () => {
        reject(new Error('Failed to remove sync queue item'));
      };
    });
  }

  async clearSyncQueue() {
    const db = await this.ensureDB();
    const transaction = db.transaction(['sync_queue'], 'readwrite');
    const store = transaction.objectStore('sync_queue');

    return new Promise((resolve, reject) => {
      const request = store.clear();

      request.onsuccess = () => {
        resolve();
      };

      request.onerror = () => {
        reject(new Error('Failed to clear sync queue'));
      };
    });
  }

  // Sync functionality
  async syncWithServer() {
    if (!navigator.onLine) {
      console.log('Offline - skipping sync');
      return { success: false, message: 'Offline' };
    }

    try {
      const syncQueue = await this.getSyncQueue();
      const results = [];

      for (const item of syncQueue) {
        try {
          let result = null;

          switch (item.action) {
            case 'update':
              result = await this.syncChecklistUpdate(item);
              break;
            case 'delete':
              result = await this.syncChecklistDelete(item);
              break;
            default:
              console.warn('Unknown sync action:', item.action);
              continue;
          }

          if (result && result.success) {
            await this.removeSyncQueueItem(item.checklist_id);
            if (item.action === 'update') {
              await this.markChecklistSynced(item.checklist_id);
            }
            results.push({ ...item, success: true });
          } else {
            results.push({ ...item, success: false, error: result?.error });
          }
        } catch (error) {
          console.error('Sync error for item:', item, error);
          results.push({ ...item, success: false, error: error.message });
        }
      }

      return {
        success: true,
        synced: results.filter(r => r.success).length,
        failed: results.filter(r => !r.success).length,
        results
      };
    } catch (error) {
      console.error('Sync with server failed:', error);
      return { success: false, error: error.message };
    }
  }

  async syncChecklistUpdate(syncItem) {
    const endpoint = syncItem.checklist_id.startsWith('local-') 
      ? `${process.env.REACT_APP_BACKEND_URL}/api/checklists`
      : `${process.env.REACT_APP_BACKEND_URL}/api/checklists/${syncItem.checklist_id}`;
    
    const method = syncItem.checklist_id.startsWith('local-') ? 'POST' : 'PUT';

    const response = await fetch(endpoint, {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(syncItem.data)
    });

    if (response.ok) {
      const result = await response.json();
      
      if (method === 'POST' && result.id) {
        // Update local ID with server ID
        const oldId = syncItem.checklist_id;
        const newId = result.id;
        
        // Delete old local entry and save with new ID
        await this.deleteChecklist(oldId);
        await this.saveChecklist({ ...result, synced: true });
      }

      return { success: true, data: result };
    } else {
      return { success: false, error: `HTTP ${response.status}` };
    }
  }

  async syncChecklistDelete(syncItem) {
    if (syncItem.checklist_id.startsWith('local-')) {
      // Local-only item, just remove from queue
      return { success: true };
    }

    const response = await fetch(
      `${process.env.REACT_APP_BACKEND_URL}/api/checklists/${syncItem.checklist_id}`,
      { method: 'DELETE' }
    );

    if (response.ok || response.status === 404) {
      return { success: true };
    } else {
      return { success: false, error: `HTTP ${response.status}` };
    }
  }

  // Utility methods
  async getStorageInfo() {
    try {
      const checklists = await this.getAllChecklists();
      const unsyncedChecklists = await this.getUnsyncedChecklists();
      const syncQueue = await this.getSyncQueue();

      return {
        total_checklists: checklists.length,
        unsynced_checklists: unsyncedChecklists.length,
        sync_queue_items: syncQueue.length,
        storage_used: await this.estimateStorageUsage()
      };
    } catch (error) {
      console.error('Error getting storage info:', error);
      return null;
    }
  }

  async estimateStorageUsage() {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      try {
        const estimate = await navigator.storage.estimate();
        return {
          used: estimate.usage,
          available: estimate.quota,
          used_mb: Math.round(estimate.usage / 1024 / 1024 * 100) / 100,
          available_mb: Math.round(estimate.quota / 1024 / 1024 * 100) / 100
        };
      } catch (error) {
        console.warn('Storage estimation failed:', error);
        return null;
      }
    }
    return null;
  }
}

// Create singleton instance
const checklistOfflineService = new ChecklistOfflineService();

export default checklistOfflineService;