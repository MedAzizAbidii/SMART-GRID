import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'dart:convert';
import 'package:flutter/foundation.dart';

class CacheService {
  static final CacheService _instance = CacheService._internal();
  static Database? _db;

  factory CacheService() {
    return _instance;
  }

  CacheService._internal();

  Future<Database> _getDatabase() async {
    if (_db != null) return _db!;

    // Skip database on web (use in-memory fallback)
    if (kIsWeb) {
      throw UnsupportedError('SQLite cache not available on web');
    }

    final databasesPath = await getDatabasesPath();
    final path = join(databasesPath, 'smartgrid_cache.db');

    _db = await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE cache (
            id TEXT PRIMARY KEY,
            key TEXT UNIQUE,
            value TEXT,
            expires_at INTEGER,
            created_at INTEGER
          )
        ''');
        await db.execute('''
          CREATE TABLE alerts (
            id TEXT PRIMARY KEY,
            title TEXT,
            body TEXT,
            type TEXT,
            data TEXT,
            read INTEGER DEFAULT 0,
            timestamp INTEGER
          )
        ''');
        await db.execute('''
          CREATE TABLE grid_data (
            id TEXT PRIMARY KEY,
            bus_id INTEGER,
            voltage REAL,
            frequency REAL,
            active_power REAL,
            reactive_power REAL,
            timestamp INTEGER
          )
        ''');
      },
    );

    return _db!;
  }

  Future<void> setCache(String key, dynamic value, {Duration? ttl}) async {
    final db = await _getDatabase();
    final expiresAt = ttl != null
        ? DateTime.now().add(ttl).millisecondsSinceEpoch
        : null;

    await db.insert(
      'cache',
      {
        'id': '${key}_${DateTime.now().millisecondsSinceEpoch}',
        'key': key,
        'value': jsonEncode(value),
        'expires_at': expiresAt,
        'created_at': DateTime.now().millisecondsSinceEpoch,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<dynamic> getCache(String key) async {
    final db = await _getDatabase();
    final result = await db.query(
      'cache',
      where: 'key = ?',
      whereArgs: [key],
      limit: 1,
    );

    if (result.isEmpty) return null;

    final row = result.first;
    final expiresAt = row['expires_at'] as int?;

    if (expiresAt != null && DateTime.now().millisecondsSinceEpoch > expiresAt) {
      await db.delete('cache', where: 'key = ?', whereArgs: [key]);
      return null;
    }

    try {
      return jsonDecode(row['value'] as String);
    } catch (e) {
      debugPrint('Cache decode error for $key: $e');
      return null;
    }
  }

  Future<void> cacheAlert(String id, Map<String, dynamic> alert) async {
    final db = await _getDatabase();
    await db.insert(
      'alerts',
      {
        'id': id,
        'title': alert['title'],
        'body': alert['body'],
        'type': alert['type'],
        'data': jsonEncode(alert['data'] ?? {}),
        'timestamp': DateTime.now().millisecondsSinceEpoch,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<Map<String, dynamic>>> getCachedAlerts({int limit = 50}) async {
    final db = await _getDatabase();
    final results = await db.query(
      'alerts',
      orderBy: 'timestamp DESC',
      limit: limit,
    );

    return results
        .map((row) {
          row['data'] = jsonDecode(row['data'] as String? ?? '{}');
          return row;
        })
        .toList();
  }

  Future<void> markAlertAsRead(String id) async {
    final db = await _getDatabase();
    await db.update(
      'alerts',
      {'read': 1},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<int> getUnreadAlertCount() async {
    final db = await _getDatabase();
    final result = await db.query(
      'alerts',
      where: 'read = 0',
    );
    return result.length;
  }

  Future<void> cacheGridData(String busId, Map<String, dynamic> data) async {
    final db = await _getDatabase();
    await db.insert(
      'grid_data',
      {
        'id': '${busId}_${DateTime.now().millisecondsSinceEpoch}',
        'bus_id': int.tryParse(busId) ?? 0,
        'voltage': (data['voltage'] as num?)?.toDouble() ?? 0.0,
        'frequency': (data['frequency'] as num?)?.toDouble() ?? 0.0,
        'active_power': (data['active_power'] as num?)?.toDouble() ?? 0.0,
        'reactive_power': (data['reactive_power'] as num?)?.toDouble() ?? 0.0,
        'timestamp': DateTime.now().millisecondsSinceEpoch,
      },
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<Map<String, dynamic>>> getCachedGridData(String busId) async {
    final db = await _getDatabase();
    return await db.query(
      'grid_data',
      where: 'bus_id = ?',
      whereArgs: [int.tryParse(busId) ?? 0],
      orderBy: 'timestamp DESC',
      limit: 100,
    );
  }

  Future<void> clearExpired() async {
    final db = await _getDatabase();
    final now = DateTime.now().millisecondsSinceEpoch;
    await db.delete(
      'cache',
      where: 'expires_at IS NOT NULL AND expires_at < ?',
      whereArgs: [now],
    );
  }

  Future<void> clearAll() async {
    final db = await _getDatabase();
    await db.delete('cache');
    await db.delete('alerts');
    await db.delete('grid_data');
  }

  Future<void> close() async {
    await _db?.close();
    _db = null;
  }
}
