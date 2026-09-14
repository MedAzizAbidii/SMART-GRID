/// Mirrors the User model returned by /api/auth/me and /api/auth/users
/// (production/security/auth.py's User pydantic model — never includes a
/// password hash).
class AppUser {
  final String username;
  final String role;
  final String fullName;

  AppUser({required this.username, required this.role, this.fullName = ''});

  factory AppUser.fromJson(Map<String, dynamic> json) => AppUser(
        username: json['username'] as String? ?? '',
        role: json['role'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
      );
}

const roleHierarchy = ['viewer', 'analyst', 'grid_operator', 'administrator'];

String roleLabel(String role) {
  switch (role) {
    case 'administrator':
      return 'Administrator';
    case 'grid_operator':
      return 'Grid Operator';
    case 'analyst':
      return 'Security Analyst';
    case 'viewer':
      return 'Viewer';
    default:
      return role;
  }
}
