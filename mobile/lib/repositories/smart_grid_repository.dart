import '../api/api_client.dart';
import '../models/alert.dart';
import '../models/blockchain.dart';
import '../models/detection.dart';
import '../models/grid.dart';
import '../models/health.dart';
import '../models/model_status.dart';
import '../models/user.dart';

/// Single source of truth between the API transport (ApiClient, raw JSON)
/// and every ViewModel (typed models). This is the layer that would change
/// if the transport ever did (e.g. adding a cache, retry policy, or
/// websocket push) — ViewModels never talk to ApiClient directly.
class SmartGridRepository {
  final ApiClient api;
  SmartGridRepository(this.api);

  // ── Auth ──────────────────────────────────────────────────────────────
  Future<AppUser> login(String username, String password) async {
    final result = await api.login(username, password);
    api.setToken(result['access_token'] as String);
    return whoAmI();
  }

  Future<AppUser> whoAmI() async => AppUser.fromJson(await api.whoAmI());

  Future<void> changePassword(String current, String next) =>
      api.changePassword(current, next);

  Future<List<AppUser>> listUsers() async =>
      (await api.listUsers()).map((u) => AppUser.fromJson(u as Map<String, dynamic>)).toList();

  Future<AppUser> createUser(String username, String password, String role, String fullName) async =>
      AppUser.fromJson(await api.createUser(username, password, role, fullName));

  Future<AppUser> updateUserRole(String username, String role) async =>
      AppUser.fromJson(await api.updateUserRole(username, role));

  Future<void> deleteUser(String username) => api.deleteUser(username);

  Future<void> resetUserPassword(String username, String newPassword) =>
      api.resetUserPassword(username, newPassword);

  // ── System ───────────────────────────────────────────────────────────
  Future<HealthStatus> getHealth() async => HealthStatus.fromJson(await api.getHealthDetailed());

  // ── AI model ─────────────────────────────────────────────────────────
  Future<ModelStatus> getModelStatus() async => ModelStatus.fromJson(await api.getModelStatus());

  Future<List<ModelVersion>> getModelVersions() async {
    final json = await api.getModelRegistry();
    return (json['versions'] as List? ?? [])
        .map((v) => ModelVersion.fromJson(v as Map<String, dynamic>))
        .toList()
        .reversed
        .toList();
  }

  Future<DetectionResult> detect(Map<String, dynamic> reading) async =>
      DetectionResult.fromJson(await api.detectReading(reading));

  // ── Blockchain ───────────────────────────────────────────────────────
  Future<BlockchainStatus> getBlockchainStatus() async =>
      BlockchainStatus.fromJson(await api.getBlockchainStatus());

  Future<OnchainStatus> getOnchainStatus() async =>
      OnchainStatus.fromJson(await api.getOnchainStatus());

  Future<Map<String, dynamic>> triggerOnchainAnchor() => api.triggerOnchainAnchor();

  // ── Grid / alerts ────────────────────────────────────────────────────
  Future<GridSnapshot> getGrid() async => GridSnapshot.fromJson(await api.getGridAll());

  Future<AlertsSnapshot> getAlerts() async => AlertsSnapshot.fromJson(await api.getAlerts());
}
