import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../api/api_client.dart';
import '../repositories/smart_grid_repository.dart';
import '../theme/app_theme.dart';

class SettingsView extends StatefulWidget {
  const SettingsView({super.key});

  @override
  State<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends State<SettingsView> {
  final _currentCtrl = TextEditingController();
  final _newCtrl = TextEditingController();
  bool _busy = false;
  String? _message;
  bool _messageIsError = false;

  @override
  void dispose() {
    _currentCtrl.dispose();
    _newCtrl.dispose();
    super.dispose();
  }

  Future<void> _changePassword() async {
    setState(() {
      _busy = true;
      _message = null;
    });
    try {
      await context.read<SmartGridRepository>().changePassword(_currentCtrl.text, _newCtrl.text);
      setState(() {
        _message = 'Password changed successfully';
        _messageIsError = false;
        _currentCtrl.clear();
        _newCtrl.clear();
      });
    } catch (e) {
      setState(() {
        _message = e is ApiException ? e.friendlyMessage : 'Failed to change password';
        _messageIsError = true;
      });
    } finally {
      setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text('CONNECTION', style: TextStyle(color: AppColors.textMuted, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5)),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text('Backend URL', style: TextStyle(color: AppColors.textMuted, fontSize: 13)),
                  Text(ApiClient.baseUrl, style: const TextStyle(color: AppColors.textPrimary, fontSize: 12, fontFamily: 'monospace')),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          const Text('CHANGE PASSWORD', style: TextStyle(color: AppColors.textMuted, fontSize: 11, fontWeight: FontWeight.w700, letterSpacing: 0.5)),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                children: [
                  TextField(
                    controller: _currentCtrl,
                    obscureText: true,
                    style: const TextStyle(color: AppColors.textPrimary),
                    decoration: const InputDecoration(labelText: 'Current password'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _newCtrl,
                    obscureText: true,
                    style: const TextStyle(color: AppColors.textPrimary),
                    decoration: const InputDecoration(labelText: 'New password'),
                  ),
                  if (_message != null) ...[
                    const SizedBox(height: 10),
                    Text(_message!, style: TextStyle(color: _messageIsError ? AppColors.critical : AppColors.success, fontSize: 12)),
                  ],
                  const SizedBox(height: 14),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _busy ? null : _changePassword,
                      child: _busy
                          ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Text('Update password'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
