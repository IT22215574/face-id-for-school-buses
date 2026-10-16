import 'package:flutter/material.dart';
import 'bus_ui.dart';

class PremiumPageTransitions extends PageTransitionsBuilder {
  const PremiumPageTransitions();
  @override
  Duration get transitionDuration => const Duration(milliseconds: 280);
  @override
  Duration get reverseTransitionDuration => const Duration(milliseconds: 220);
  @override
  Widget buildTransitions<T>(
      PageRoute<T> route,
      BuildContext context,
      Animation<double> animation,
      Animation<double> secondaryAnimation,
      Widget child) {
    if (MediaQuery.disableAnimationsOf(context)) return child;
    final curved = CurvedAnimation(
        parent: animation,
        curve: Curves.easeOutCubic,
        reverseCurve: Curves.easeInCubic);
    return FadeTransition(
        opacity: curved,
        child: SlideTransition(
          position:
              Tween<Offset>(begin: const Offset(0.025, 0.015), end: Offset.zero)
                  .animate(curved),
          child: child,
        ));
  }
}

ThemeData buildAppTheme() => ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
          seedColor: busBlue,
          primary: busBlue,
          secondary: const Color(0xFF0891B2),
          surface: Colors.white),
      scaffoldBackgroundColor: busBackground,
      fontFamily: 'Roboto',
      textTheme: ThemeData.light()
          .textTheme
          .apply(bodyColor: busText, displayColor: busText)
          .copyWith(
            bodyMedium:
                const TextStyle(fontSize: 14, height: 1.5, color: busText),
            titleLarge: const TextStyle(
                fontSize: 22,
                height: 1.25,
                fontWeight: FontWeight.w700,
                letterSpacing: -0.5,
                color: busText),
          ),
      pageTransitionsTheme: PageTransitionsTheme(builders: {
        for (final platform in TargetPlatform.values)
          platform: const PremiumPageTransitions(),
      }),
      appBarTheme: const AppBarTheme(
        backgroundColor: busBlue,
        foregroundColor: Colors.white,
        elevation: 0,
        scrolledUnderElevation: 0,
        toolbarHeight: 76,
        titleTextStyle: TextStyle(
            fontSize: 22,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.5,
            color: Colors.white),
      ),
      filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
        minimumSize: const Size(48, 54),
        padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 14),
        textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      )),
      outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
        minimumSize: const Size(48, 52),
        side: const BorderSide(color: Color(0xFFD7E2EF)),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      )),
      textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
        minimumSize: const Size(48, 48),
        textStyle: const TextStyle(fontWeight: FontWeight.w600),
      )),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        contentPadding: const EdgeInsets.all(18),
        prefixIconColor: busMuted,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(16)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: Color(0xFFE1E8F2))),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(16),
            borderSide: const BorderSide(color: busBlue, width: 2)),
      ),
      snackBarTheme: SnackBarThemeData(
          behavior: SnackBarBehavior.floating,
          backgroundColor: busText,
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(16))),
      dividerTheme:
          const DividerThemeData(color: Color(0xFFE6ECF4), thickness: 1),
    );
