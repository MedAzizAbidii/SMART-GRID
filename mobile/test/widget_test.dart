import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:smartgrid_mobile/main.dart';

void main() {
  testWidgets('App boots to the login screen when unauthenticated', (WidgetTester tester) async {
    await tester.pumpWidget(const SmartGridApp());
    // First frame: AuthViewModel is still restoring session state from
    // SharedPreferences (async) — settle lets that resolve before asserting.
    await tester.pumpAndSettle();

    expect(find.text('GridSentinel'), findsOneWidget);
    expect(find.widgetWithText(ElevatedButton, 'Sign in'), findsOneWidget);
  });
}
