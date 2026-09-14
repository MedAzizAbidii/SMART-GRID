import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/user.dart';
import '../theme/app_theme.dart';
import '../viewmodels/users_viewmodel.dart';
import '../widgets/common.dart';

class UsersView extends StatelessWidget {
  const UsersView({super.key});

  @override
  Widget build(BuildContext context) {
    final vm = context.watch<UsersViewModel>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Users'),
        actions: [
          IconButton(icon: const Icon(Icons.person_add_alt_1), onPressed: () => _showCreateDialog(context, vm)),
        ],
      ),
      body: vm.loading
          ? const LoadingView()
          : vm.error != null
              ? ErrorView(message: vm.error!)
              : RefreshIndicator(
                  onRefresh: vm.load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: vm.users.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 8),
                    itemBuilder: (context, i) {
                      final u = vm.users[i];
                      return Card(
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: AppColors.dim(AppColors.primary),
                            child: Text(u.username.isNotEmpty ? u.username[0].toUpperCase() : '?',
                                style: const TextStyle(color: AppColors.primary, fontWeight: FontWeight.w700)),
                          ),
                          title: Text(u.username, style: const TextStyle(color: AppColors.textPrimary, fontWeight: FontWeight.w600)),
                          subtitle: Text(roleLabel(u.role), style: const TextStyle(color: AppColors.textMuted, fontSize: 12)),
                          trailing: PopupMenuButton<String>(
                            icon: const Icon(Icons.more_vert, color: AppColors.textMuted),
                            onSelected: (action) => _handleAction(context, vm, u, action),
                            itemBuilder: (context) => [
                              const PopupMenuItem(value: 'role', child: Text('Change role')),
                              const PopupMenuItem(value: 'reset', child: Text('Reset password')),
                              const PopupMenuItem(value: 'delete', child: Text('Delete')),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
    );
  }

  void _handleAction(BuildContext context, UsersViewModel vm, AppUser u, String action) async {
    switch (action) {
      case 'role':
        _showRoleDialog(context, vm, u);
      case 'reset':
        _showResetDialog(context, vm, u);
      case 'delete':
        final confirmed = await showDialog<bool>(
          context: context,
          builder: (_) => AlertDialog(
            backgroundColor: AppColors.card,
            title: const Text('Delete user?', style: TextStyle(color: AppColors.textPrimary)),
            content: Text('This removes ${u.username} permanently.', style: const TextStyle(color: AppColors.textSecondary)),
            actions: [
              TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
              TextButton(onPressed: () => Navigator.pop(context, true), child: const Text('Delete', style: TextStyle(color: AppColors.critical))),
            ],
          ),
        );
        if (confirmed == true) {
          final err = await vm.deleteUser(u.username);
          if (context.mounted && err != null) _showSnack(context, err);
        }
    }
  }

  void _showCreateDialog(BuildContext context, UsersViewModel vm) {
    final userCtrl = TextEditingController();
    final passCtrl = TextEditingController();
    final nameCtrl = TextEditingController();
    String role = 'viewer';

    showDialog(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setState) => AlertDialog(
          backgroundColor: AppColors.card,
          title: const Text('New user', style: TextStyle(color: AppColors.textPrimary)),
          content: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TextField(controller: userCtrl, decoration: const InputDecoration(labelText: 'Username'), style: const TextStyle(color: AppColors.textPrimary)),
              const SizedBox(height: 10),
              TextField(controller: passCtrl, obscureText: true, decoration: const InputDecoration(labelText: 'Password'), style: const TextStyle(color: AppColors.textPrimary)),
              const SizedBox(height: 10),
              TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Full name'), style: const TextStyle(color: AppColors.textPrimary)),
              const SizedBox(height: 10),
              DropdownButtonFormField<String>(
                initialValue: role,
                dropdownColor: AppColors.card,
                style: const TextStyle(color: AppColors.textPrimary),
                items: roleHierarchy.map((r) => DropdownMenuItem(value: r, child: Text(roleLabel(r)))).toList(),
                onChanged: (v) => setState(() => role = v ?? role),
              ),
            ]),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () async {
                final err = await vm.createUser(userCtrl.text.trim(), passCtrl.text, role, nameCtrl.text.trim());
                if (dialogContext.mounted) Navigator.pop(dialogContext);
                if (context.mounted && err != null) _showSnack(context, err);
              },
              child: const Text('Create'),
            ),
          ],
        ),
      ),
    );
  }

  void _showRoleDialog(BuildContext context, UsersViewModel vm, AppUser u) {
    String role = u.role;
    showDialog(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setState) => AlertDialog(
          backgroundColor: AppColors.card,
          title: Text('Role for ${u.username}', style: const TextStyle(color: AppColors.textPrimary)),
          content: DropdownButtonFormField<String>(
            initialValue: role,
            dropdownColor: AppColors.card,
            style: const TextStyle(color: AppColors.textPrimary),
            items: roleHierarchy.map((r) => DropdownMenuItem(value: r, child: Text(roleLabel(r)))).toList(),
            onChanged: (v) => setState(() => role = v ?? role),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () async {
                final err = await vm.updateRole(u.username, role);
                if (dialogContext.mounted) Navigator.pop(dialogContext);
                if (context.mounted && err != null) _showSnack(context, err);
              },
              child: const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }

  void _showResetDialog(BuildContext context, UsersViewModel vm, AppUser u) {
    final passCtrl = TextEditingController();
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: AppColors.card,
        title: Text('Reset password for ${u.username}', style: const TextStyle(color: AppColors.textPrimary)),
        content: TextField(controller: passCtrl, obscureText: true, decoration: const InputDecoration(labelText: 'New password'), style: const TextStyle(color: AppColors.textPrimary)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Cancel')),
          ElevatedButton(
            onPressed: () async {
              final err = await vm.resetPassword(u.username, passCtrl.text);
              if (dialogContext.mounted) Navigator.pop(dialogContext);
              if (context.mounted) _showSnack(context, err ?? 'Password reset');
            },
            child: const Text('Reset'),
          ),
        ],
      ),
    );
  }

  void _showSnack(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }
}
