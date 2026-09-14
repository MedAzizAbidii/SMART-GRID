import 'dart:async';
import 'package:flutter/foundation.dart';

/// Base for any ViewModel that needs to repeatedly re-fetch from the
/// backend — mirrors the web dashboard's usePolling hook so every screen
/// follows the same load/error/refresh contract instead of hand-rolling
/// Timer logic nine times over.
abstract class PollingViewModel extends ChangeNotifier {
  bool loading = true;
  String? error;
  Timer? _timer;

  Duration get interval;

  void start() {
    refresh();
    _timer = Timer.periodic(interval, (_) => refresh());
  }

  Future<void> refresh() async {
    try {
      await fetch();
      error = null;
    } catch (e) {
      // Demo mode on web: ignore errors and show last known data
      if (!kIsWeb) {
        error = friendlyError(e);
      }
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  /// Subclasses implement the actual repository calls and assign results
  /// to their own fields, then this base class handles loading/error/timer.
  Future<void> fetch();

  String friendlyError(Object e) => 'Cannot reach server';

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}
