import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../repositories/smart_grid_repository.dart';
import '../viewmodels/ai_detection_viewmodel.dart';
import '../viewmodels/alerts_viewmodel.dart';
import '../viewmodels/blockchain_viewmodel.dart';
import '../viewmodels/cybersecurity_viewmodel.dart';
import '../viewmodels/explainable_ai_viewmodel.dart';
import '../viewmodels/grid_viewmodel.dart';
import '../viewmodels/meters_viewmodel.dart';
import '../viewmodels/monitoring_viewmodel.dart';
import '../viewmodels/theft_viewmodel.dart';
import '../viewmodels/users_viewmodel.dart';
import '../views/ai_detection_view.dart';
import '../views/alerts_view.dart';
import '../views/blockchain_view.dart';
import '../views/cybersecurity_view.dart';
import '../views/explainable_ai_view.dart';
import '../views/grid_view.dart';
import '../views/meters_view.dart';
import '../views/monitoring_view.dart';
import '../views/theft_view.dart';
import '../views/users_view.dart';

/// Central place every "drill down from Home / More" navigation goes
/// through. Each screen owns a freshly-created, self-starting ViewModel
/// scoped to its own Navigator route — polling starts only while the
/// screen is actually visible and stops on pop (ViewModel.dispose()).
class AppRoutes {
  static void pushGrid(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => GridViewModel(repo)..start(), child: const GridScreenView()),
    ));
  }

  static void pushMeters(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => MetersViewModel(repo)..start(), child: const MetersView()),
    ));
  }

  static void pushAiDetection(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => AiDetectionViewModel(repo), child: const AiDetectionView()),
    ));
  }

  static void pushExplainableAi(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => ExplainableAiViewModel(repo), child: const ExplainableAiView()),
    ));
  }

  static void pushCybersecurity(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => CybersecurityViewModel(repo)..start(), child: const CybersecurityView()),
    ));
  }

  static void pushTheft(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => TheftViewModel(repo)..start(), child: const TheftView()),
    ));
  }

  static void pushMonitoring(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => MonitoringViewModel(repo)..start(), child: const MonitoringView()),
    ));
  }

  static void pushAlerts(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => AlertsViewModel(repo)..start(), child: const AlertsView()),
    ));
  }

  static void pushBlockchain(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => BlockchainViewModel(repo)..start(), child: const BlockchainView()),
    ));
  }

  static void pushUsers(BuildContext context) {
    final repo = context.read<SmartGridRepository>();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => ChangeNotifierProvider(create: (_) => UsersViewModel(repo)..load(), child: const UsersView()),
    ));
  }
}
