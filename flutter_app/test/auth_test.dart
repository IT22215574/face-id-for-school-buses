import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:school_bus_parent_app/app.dart';
import 'package:school_bus_parent_app/core/api_client.dart';
import 'package:school_bus_parent_app/features/auth/login_screen.dart';
import 'package:school_bus_parent_app/features/driver/driver_screen.dart';
import 'package:school_bus_parent_app/features/transport/student_screens.dart';
import 'package:school_bus_parent_app/features/transport/transport_state.dart';
import 'package:school_bus_parent_app/providers/auth_provider.dart';
import 'package:school_bus_parent_app/services/auth_service.dart';

class TestAuthService extends AuthService {
  TestAuthService()
      : super(const FlutterSecureStorage(),
            ApiClient(const FlutterSecureStorage()));
  bool signedOut = false;
  @override
  Future<AccountRole?> register(
      String name, String phone, String email, String password) async {
    expect(name, 'Test Parent');
    expect(phone, '0771234567');
    expect(email, 'parent@example.com');
    return AccountRole.parent;
  }

  @override
  Future<AccountRole?> login(String email, String password) async {
    if (email == 'parent@example.com' && password == 'password123') {
      return AccountRole.parent;
    }
    if (email == 'driver@example.com' && password == 'driver123') {
      return AccountRole.driver;
    }
    final request = RequestOptions(path: '/auth/login');
    throw DioException(
        requestOptions: request,
        response: Response(requestOptions: request, statusCode: 401),
        type: DioExceptionType.badResponse);
  }

  @override
  Future<void> logout() async {
    signedOut = true;
  }
}

void main() {
  Future<void> submit(
      WidgetTester tester, String email, String password) async {
    await tester.enterText(find.byType(TextFormField).at(0), email);
    await tester.enterText(find.byType(TextFormField).at(1), password);
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
  }

  testWidgets('Parent signup validates confirmation and opens child selection',
      (tester) async {
    tester.view.physicalSize = const Size(500, 1100);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(ProviderScope(overrides: [
      transportLoadProvider.overrideWith((ref) async {}),
      transportStudentsProvider.overrideWith((ref) => []),
      authServiceProvider.overrideWithValue(TestAuthService()),
    ], child: const SchoolBusParentApp()));
    await tester.pumpAndSettle();
    await tester.tap(find.text('New parent? Sign up'));
    await tester.pumpAndSettle();
    final fields = find.byType(TextFormField);
    for (final entry in [
      'Test Parent',
      '0771234567',
      'parent@example.com',
      'password123',
      'wrong'
    ].asMap().entries) {
      await tester.enterText(fields.at(entry.key), entry.value);
    }
    await tester.ensureVisible(find.text('Create account'));
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();
    expect(find.text('Passwords do not match'), findsOneWidget);
    await tester.enterText(fields.at(4), 'password123');
    await tester.ensureVisible(find.text('Create account'));
    await tester.tap(find.text('Create account'));
    await tester.pumpAndSettle();
    expect(find.byType(SelectChildScreen), findsOneWidget);
    expect(find.textContaining('No children added yet'), findsOneWidget);
  });

  for (final driver in [false, true]) {
    testWidgets(
        '${driver ? 'Driver' : 'Parent'} credentials open only the matching flow',
        (tester) async {
      tester.view.physicalSize = const Size(402, 874);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final service = TestAuthService();
      await tester.pumpWidget(ProviderScope(overrides: [
        transportLoadProvider.overrideWith((ref) async {}),
        transportStudentsProvider.overrideWith(
            (ref) => [const TransportStudent(name: 'Kavindu Perera')]),
        authServiceProvider.overrideWithValue(service)
      ], child: const SchoolBusParentApp()));
      await tester.pumpAndSettle();
      expect(find.byType(LoginScreen), findsOneWidget);
      await submit(tester, driver ? 'driver@example.com' : 'parent@example.com',
          driver ? 'driver123' : 'password123');
      if (driver) {
        expect(find.byType(DriverScreen), findsOneWidget);
        expect(find.byType(SelectChildScreen), findsNothing);
      } else {
        expect(find.byType(SelectChildScreen), findsOneWidget);
        expect(find.byType(DriverScreen), findsNothing);
        await tester.tap(find.byTooltip('Kavindu Perera'));
        await tester.pumpAndSettle();
      }
      await tester.tap(find.byTooltip('Sign out'));
      await tester.pumpAndSettle();
      expect(service.signedOut, isTrue);
      expect(find.byType(LoginScreen), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
  testWidgets('Invalid credentials show an error and allow another attempt',
      (tester) async {
    await tester.pumpWidget(ProviderScope(overrides: [
      transportLoadProvider.overrideWith((ref) async {}),
      transportStudentsProvider.overrideWith(
          (ref) => [const TransportStudent(name: 'Kavindu Perera')]),
      authServiceProvider.overrideWithValue(TestAuthService())
    ], child: const SchoolBusParentApp()));
    await tester.pumpAndSettle();
    await submit(tester, 'driver@example.com', 'incorrect-password');
    expect(find.text('Invalid email or password.'), findsOneWidget);
    expect(find.byType(DriverScreen), findsNothing);
    await submit(tester, 'driver@example.com', 'driver123');
    expect(find.byType(DriverScreen), findsOneWidget);
  });
}
