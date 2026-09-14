import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class SectionHeader extends StatelessWidget {
  final String title;
  final Widget? action;
  const SectionHeader({super.key, required this.title, this.action});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: const TextStyle(
              color: AppColors.textPrimary, fontWeight: FontWeight.w700, fontSize: 15)),
          ?action,
        ],
      ),
    );
  }
}

class LoadingView extends StatelessWidget {
  const LoadingView({super.key});
  @override
  Widget build(BuildContext context) => const Center(child: CircularProgressIndicator());
}

class ErrorView extends StatelessWidget {
  final String message;
  const ErrorView({super.key, required this.message});
  @override
  Widget build(BuildContext context) => ListView(
        children: [
          const SizedBox(height: 80),
          const Icon(Icons.cloud_off, color: AppColors.textMuted, size: 40),
          const SizedBox(height: 12),
          Center(child: Text(message, style: const TextStyle(color: AppColors.textMuted))),
        ],
      );
}

class EmptyView extends StatelessWidget {
  final IconData icon;
  final String message;
  const EmptyView({super.key, this.icon = Icons.inbox_outlined, required this.message});
  @override
  Widget build(BuildContext context) => ListView(
        children: [
          const SizedBox(height: 60),
          Icon(icon, color: AppColors.textMuted, size: 36),
          const SizedBox(height: 12),
          Center(child: Text(message, textAlign: TextAlign.center, style: const TextStyle(color: AppColors.textMuted))),
        ],
      );
}

/// Mirrors the web dashboard's MockFlag component — an explicit, honest
/// marker for the few fields that aren't backed by a live measurement
/// (e.g. illustrative SHAP values, since SHAP is offline-only in
/// production). Never used to disguise a fabricated number as real.
class SampleDataTag extends StatelessWidget {
  const SampleDataTag({super.key});
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: AppColors.card,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: AppColors.border),
        ),
        child: const Text('● Sample data — no live backend source',
            style: TextStyle(color: AppColors.textMuted, fontSize: 10, fontWeight: FontWeight.w600)),
      );
}

class FilterChip2 extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;
  const FilterChip2({super.key, required this.label, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: selected ? AppColors.dim(AppColors.primary) : AppColors.card,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: selected ? AppColors.primary.withValues(alpha: 0.4) : AppColors.border),
        ),
        child: Text(label, style: TextStyle(
            color: selected ? AppColors.primary : AppColors.textSecondary,
            fontSize: 12.5, fontWeight: FontWeight.w600)),
      ),
    );
  }
}

class SearchField extends StatelessWidget {
  final String hint;
  final ValueChanged<String> onChanged;
  const SearchField({super.key, required this.hint, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return TextField(
      onChanged: onChanged,
      style: const TextStyle(color: AppColors.textPrimary, fontSize: 14),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: AppColors.textMuted, fontSize: 13),
        prefixIcon: const Icon(Icons.search, color: AppColors.textMuted, size: 20),
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(vertical: 12),
      ),
    );
  }
}

class ProgressBar extends StatelessWidget {
  final double value; // 0-100
  final String tone;
  final double height;
  const ProgressBar({super.key, required this.value, this.tone = 'primary', this.height = 6});

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(999),
      child: Container(
        height: height,
        color: Colors.white.withValues(alpha: 0.06),
        alignment: Alignment.centerLeft,
        child: FractionallySizedBox(
          widthFactor: (value / 100).clamp(0, 1),
          child: Container(color: toneColor(tone)),
        ),
      ),
    );
  }
}
