import 'package:flutter/foundation.dart';
import '../api/api_client.dart';
import '../models/user.dart';
import '../repositories/smart_grid_repository.dart';

/// Admin-only user management — the real CRUD API this project shipped to
/// replace hand-editing users.json, now consumed by a real client for the
/// first time.
class UsersViewModel extends ChangeNotifier {
  final SmartGridRepository repo;
  UsersViewModel(this.repo);

  List<AppUser> users = [];
  bool loading = true;
  String? error;
  bool busy = false;

  Future<void> load() async {
    loading = true;
    notifyListeners();
    try {
      users = await repo.listUsers();
      error = null;
    } catch (e) {
      error = e is ApiException ? e.friendlyMessage : 'Cannot reach server';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<String?> createUser(String username, String password, String role, String fullName) async {
    busy = true;
    notifyListeners();
    try {
      await repo.createUser(username, password, role, fullName);
      await load();
      return null;
    } catch (e) {
      return e is ApiException ? e.friendlyMessage : 'Failed to create user';
    } finally {
      busy = false;
      notifyListeners();
    }
  }

  Future<String?> updateRole(String username, String role) async {
    try {
      await repo.updateUserRole(username, role);
      await load();
      return null;
    } catch (e) {
      return e is ApiException ? e.friendlyMessage : 'Failed to update role';
    }
  }

  Future<String?> deleteUser(String username) async {
    try {
      await repo.deleteUser(username);
      await load();
      return null;
    } catch (e) {
      return e is ApiException ? e.friendlyMessage : 'Failed to delete user';
    }
  }

  Future<String?> resetPassword(String username, String newPassword) async {
    try {
      await repo.resetUserPassword(username, newPassword);
      return null;
    } catch (e) {
      return e is ApiException ? e.friendlyMessage : 'Failed to reset password';
    }
  }
}
