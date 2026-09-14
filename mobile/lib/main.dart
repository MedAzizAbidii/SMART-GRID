import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'api/api_client.dart';
import 'repositories/smart_grid_repository.dart';
import 'theme/app_theme.dart';
import 'viewmodels/alerts_viewmodel.dart';
import 'viewmodels/auth_viewmodel.dart';
import 'viewmodels/dashboard_viewmodel.dart';
import 'viewmodels/grid_viewmodel.dart';
import 'views/alerts_view.dart';
import 'views/grid_view.dart';
import 'views/home_view.dart';
import 'views/login_view.dart';
import 'views/more_view.dart';
import 'services/firebase_service.dart';
import 'services/websocket_service.dart';
import 'services/cache_service.dart';
import 'services/app_version_service.dart';
import 'services/biometric_service.dart';
import 'services/session_timeout_service.dart';
import 'services/app_lifecycle_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Initialize all production services
  await FirebaseService.initialize();
  await AppVersionService().initialize();
  await BiometricService().initialize();

  CacheService().clearExpired();
  AppLifecycleService().initialize();
  SessionTimeoutService().startMonitoring();

  runApp(const SmartGridApp());
}

class SmartGridApp extends StatelessWidget {
  const SmartGridApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiClient>(create: (_) => ApiClient()),
        ProxyProvider<ApiClient, SmartGridRepository>(
          update: (_, api, _) => SmartGridRepository(api),
        ),
        ChangeNotifierProvider<AuthViewModel>(
          create: (ctx) => AuthViewModel(ctx.read<SmartGridRepository>(), ctx.read<ApiClient>()),
        ),
      ],
      child: MaterialApp(
        title: 'GridSentinel',
        debugShowCheckedModeBanner: false,
        theme: appTheme,
        home: const RootGate(),
      ),
    );
  }
}

/// Routes to Login or the authenticated shell based on session state — the
/// first client in this project to actually exercise the login flow
/// end-to-end (the web dashboard has no login UI yet).
class RootGate extends StatelessWidget {
  const RootGate({super.key});

  @override
  Widget build(BuildContext context) {
    final status = context.watch<AuthViewModel>().status;
    switch (status) {
      case AuthStatus.unknown:
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      case AuthStatus.unauthenticated:
        return const LoginView();
      case AuthStatus.authenticated:
        return const AppShell();
    }
  }
}

class AppShell extends StatefulWidget {
  const AppShell({super.key});

  @override
  State<AppShell> createState() => _AppShellState();
}

class _AppShellState extends State<AppShell> {
  int _index = 0;
  late final DashboardViewModel _dashboardVm;
  late final GridViewModel _gridVm;
  late final AlertsViewModel _alertsVm;

  @override
  void initState() {
    super.initState();
    final repo = context.read<SmartGridRepository>();
    _dashboardVm = DashboardViewModel(repo)..start();
    _gridVm = GridViewModel(repo)..start();
    _alertsVm = AlertsViewModel(repo)..start();
  }

  @override
  void dispose() {
    _dashboardVm.dispose();
    _gridVm.dispose();
    _alertsVm.dispose();
    WebSocketService().dispose();
    FirebaseService().dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final tabs = [
      ChangeNotifierProvider.value(value: _dashboardVm, child: const HomeView()),
      ChangeNotifierProvider.value(value: _gridVm, child: const GridScreenView()),
      ChangeNotifierProvider.value(value: _alertsVm, child: const AlertsView()),
      const MoreView(),
    ];

    return Scaffold(
      body: IndexedStack(index: _index, children: tabs),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        backgroundColor: AppColors.card,
        indicatorColor: AppColors.dim(AppColors.primary),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.hub_outlined), selectedIcon: Icon(Icons.hub), label: 'Grid'),
          NavigationDestination(icon: Icon(Icons.notifications_outlined), selectedIcon: Icon(Icons.notifications), label: 'Alerts'),
          NavigationDestination(icon: Icon(Icons.menu), selectedIcon: Icon(Icons.menu), label: 'More'),
        ],
      ),
    );
  }
}
