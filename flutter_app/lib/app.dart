import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'features/auth/splash_screen.dart';
import 'core/bus_ui.dart';

class SchoolBusParentApp extends ConsumerWidget {
  const SchoolBusParentApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'School Bus',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: busBlue, primary: busBlue),
        scaffoldBackgroundColor: busBackground,
        fontFamily: 'Roboto',
        textTheme: ThemeData.light()
            .textTheme
            .copyWith(
                bodyMedium: const TextStyle(
                    fontFamily: 'Roboto', fontSize: 14, height: 1.2))
            .apply(
                fontFamily: 'Roboto',
                bodyColor: busText,
                displayColor: busText),
        appBarTheme: const AppBarTheme(
            backgroundColor: busBlue,
            foregroundColor: Colors.white,
            elevation: 3,
            titleTextStyle: TextStyle(
                fontSize: 24,
                fontFamily: 'Roboto',
                fontWeight: FontWeight.bold,
                color: Colors.white)),
        filledButtonTheme: FilledButtonThemeData(
            style: FilledButton.styleFrom(
                backgroundColor: busBlue,
                foregroundColor: Colors.white,
                minimumSize: const Size(48, 52),
                shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20)))),
        inputDecorationTheme: InputDecorationTheme(
            filled: true,
            fillColor: Colors.white,
            contentPadding: const EdgeInsets.all(16),
            border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0xFFE2E8F0))),
            enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: const BorderSide(color: Color(0xFFE2E8F0)))),
        useMaterial3: true,
      ),
      home: const SplashScreen(),
    );
  }
}
