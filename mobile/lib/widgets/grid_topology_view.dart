import 'package:flutter/material.dart';
import '../models/grid.dart';
import '../theme/app_theme.dart';

const _typeColor = {
  'residential': AppColors.primary,
  'commercial': AppColors.info,
  'industrial': Color(0xFF8B5CF6),
};

Color _attackColor(String attackType) {
  switch (attackType) {
    case 'fdia':
    case 'fraud':
      return AppColors.critical;
    case 'dos':
    case 'fault':
      return AppColors.warning;
    default:
      return AppColors.textMuted;
  }
}

class _NodePos {
  final GridBus bus;
  final Offset offset;
  _NodePos(this.bus, this.offset);
}

/// Real-topology view of the simulator's substation + N buses — same
/// layout concept as the web dashboard's GridNetwork.jsx (fixed cols/rows
/// grid fed from one substation node), reimplemented as Flutter widgets so
/// nodes stay natively tappable.
class GridTopologyView extends StatelessWidget {
  final List<GridBus> buses;
  final int? selectedBusId;
  final ValueChanged<int> onSelect;
  final double height;

  const GridTopologyView({
    super.key,
    required this.buses,
    required this.onSelect,
    this.selectedBusId,
    this.height = 260,
  });

  List<_NodePos> _layout(Size size) {
    const cols = 5;
    final marginX = size.width * 0.12;
    final marginY = size.height * 0.28;
    final stepX = buses.length > 1 ? (size.width - marginX * 2) / (cols - 1) : 0.0;
    final stepY = size.height - marginY * 2;
    return List.generate(buses.length, (i) {
      final col = i % cols;
      final row = i ~/ cols;
      final rows = (buses.length / cols).ceil();
      final y = rows > 1 ? marginY + stepY * row / (rows - 1) : marginY;
      return _NodePos(buses[i], Offset(marginX + stepX * col, y));
    });
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: height,
      width: double.infinity,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final size = Size(constraints.maxWidth, height);
          final nodes = _layout(size);
          final substation = Offset(size.width / 2, 20);

          return Stack(
            children: [
              CustomPaint(
                size: size,
                painter: _FeederPainter(nodes, substation),
              ),
              Positioned(
                left: substation.dx - 12,
                top: substation.dy - 12,
                child: Container(
                  width: 24, height: 24,
                  decoration: BoxDecoration(
                    color: AppColors.background,
                    shape: BoxShape.circle,
                    border: Border.all(color: AppColors.primary, width: 2),
                  ),
                ),
              ),
              for (final n in nodes)
                Positioned(
                  left: n.offset.dx - 16,
                  top: n.offset.dy - 16,
                  child: GestureDetector(
                    onTap: () => onSelect(n.bus.busId),
                    child: _NodeDot(bus: n.bus, selected: n.bus.busId == selectedBusId),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}

class _NodeDot extends StatelessWidget {
  final GridBus bus;
  final bool selected;
  const _NodeDot({required this.bus, required this.selected});

  @override
  Widget build(BuildContext context) {
    final color = bus.isAttacked ? _attackColor(bus.attackType) : (_typeColor[bus.consumerType] ?? AppColors.textMuted);
    return Column(
      children: [
        Container(
          width: 32, height: 32,
          decoration: BoxDecoration(
            color: AppColors.card,
            shape: BoxShape.circle,
            border: Border.all(color: color, width: selected ? 3 : 2),
            boxShadow: bus.isAttacked
                ? [BoxShadow(color: color.withValues(alpha: 0.5), blurRadius: 8, spreadRadius: 1)]
                : null,
          ),
          child: Center(
            child: Container(width: 12, height: 12, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          ),
        ),
      ],
    );
  }
}

class _FeederPainter extends CustomPainter {
  final List<_NodePos> nodes;
  final Offset substation;
  _FeederPainter(this.nodes, this.substation);

  @override
  void paint(Canvas canvas, Size size) {
    for (final n in nodes) {
      final color = n.bus.isAttacked ? _attackColor(n.bus.attackType) : AppColors.border;
      final paint = Paint()
        ..color = color
        ..strokeWidth = n.bus.isAttacked ? 2 : 1;
      canvas.drawLine(substation, n.offset, paint);
    }
  }

  @override
  bool shouldRepaint(covariant _FeederPainter oldDelegate) => true;
}
