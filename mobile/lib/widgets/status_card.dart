import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// KPI-style tile — mirrors the web dashboard's KPICard.jsx visually
/// (icon chip, label, big value, tone-colored accents).
class StatusCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final String tone;
  final String? subtitle;

  const StatusCard({
    super.key,
    required this.icon,
    required this.label,
    required this.value,
    this.tone = 'primary',
    this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    final color = toneColor(tone);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppColors.dim(color),
                    borderRadius: BorderRadius.circular(9),
                  ),
                  child: Icon(icon, color: color, size: 19),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(label,
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 12, fontWeight: FontWeight.w500)),
            const SizedBox(height: 2),
            Text(value,
                style: const TextStyle(
                    color: AppColors.textPrimary, fontSize: 20, fontWeight: FontWeight.w700)),
            if (subtitle != null) ...[
              const SizedBox(height: 2),
              Text(subtitle!, style: const TextStyle(color: AppColors.textMuted, fontSize: 11)),
            ],
          ],
        ),
      ),
    );
  }
}

class StatusBadge extends StatelessWidget {
  final String label;
  final String tone;
  const StatusBadge({super.key, required this.label, this.tone = 'neutral'});

  @override
  Widget build(BuildContext context) {
    final color = tone == 'neutral' ? AppColors.textSecondary : toneColor(tone);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: tone == 'neutral' ? AppColors.card : AppColors.dim(color),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: tone == 'neutral' ? AppColors.border : color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6, height: 6,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Text(label, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}
