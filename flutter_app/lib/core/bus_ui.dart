import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../features/profile/profile_screen.dart';

const busBlue = Color(0xFF2563EB);
const busBackground = Color(0xFFF4F7FC);
const busText = Color(0xFF172B4D);
const busMuted = Color(0xFF64748B);

const busGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [Color(0xFF132D65), Color(0xFF2563EB), Color(0xFF0891B2)],
);
const busSoftGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [Color(0xFFEAF1FF), Color(0xFFF0FDFA)],
);

class DesignAsset extends StatelessWidget {
  const DesignAsset(this.file,
      {super.key, required this.width, required this.height});
  final String file;
  final double width;
  final double height;
  @override
  Widget build(BuildContext context) =>
      SvgPicture.asset('assets/figma/$file', width: width, height: height);
}

class BusCard extends StatelessWidget {
  const BusCard(
      {super.key,
      required this.child,
      this.padding = const EdgeInsets.all(16),
      this.color = Colors.white,
      this.radius = 20});
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color color;
  final double radius;
  @override
  Widget build(BuildContext context) => Container(
        padding: padding,
        decoration: BoxDecoration(
            color: color,
            border: Border.all(color: const Color(0xFFE6ECF4)),
            borderRadius: BorderRadius.circular(radius),
            boxShadow: const [
              BoxShadow(
                  color: Color(0x0C173B65),
                  blurRadius: 24,
                  offset: Offset(0, 8))
            ]),
        child: Material(color: Colors.transparent, child: child),
      );
}

void openScreen(BuildContext context, Widget screen, {String? name}) =>
    Navigator.of(context).push(MaterialPageRoute<void>(
        settings: RouteSettings(name: name), builder: (_) => screen));

class BusScaffold extends StatelessWidget {
  const BusScaffold(
      {super.key,
      required this.title,
      required this.child,
      this.padding = const EdgeInsets.all(26)});
  final String title;
  final Widget child;
  final EdgeInsetsGeometry padding;
  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(
            title: Text(title),
            toolbarHeight: 76,
            flexibleSpace: const DecoratedBox(
                decoration: BoxDecoration(gradient: busGradient)),
            shape: const RoundedRectangleBorder(
                borderRadius:
                    BorderRadius.vertical(bottom: Radius.circular(24)))),
        body: SafeArea(
            top: false,
            child: Align(
                alignment: Alignment.topCenter,
                child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 600),
                    child: SingleChildScrollView(
                        padding: padding, child: child)))),
        bottomNavigationBar: const BusBottomBar(),
      );
}

class BusBottomBar extends StatelessWidget {
  const BusBottomBar({super.key, this.onHome, this.onSwitch});
  final VoidCallback? onHome;
  final VoidCallback? onSwitch;
  @override
  Widget build(BuildContext context) {
    final profile = ModalRoute.of(context)?.settings.name == 'profile';
    final home = onHome != null ||
        ModalRoute.of(context)?.settings.name == 'transport-home';
    Widget item(
            String label, IconData icon, VoidCallback? onTap, bool selected) =>
        Expanded(
          child: Tooltip(
              message: label,
              child: Semantics(
                  selected: selected,
                  child: TextButton(
                    style: TextButton.styleFrom(
                        foregroundColor: selected ? busBlue : busMuted,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 4, vertical: 8)),
                    onPressed: onTap,
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      AnimatedContainer(
                          duration: MediaQuery.disableAnimationsOf(context)
                              ? Duration.zero
                              : const Duration(milliseconds: 180),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 20, vertical: 5),
                          decoration: BoxDecoration(
                              color: selected
                                  ? const Color(0xFFEAF1FF)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(16)),
                          child: Icon(icon, size: 24)),
                      const SizedBox(height: 4),
                      Text(label,
                          style: const TextStyle(
                              fontSize: 12, fontWeight: FontWeight.w600)),
                    ]),
                  ))),
        );
    return DecoratedBox(
      decoration: const BoxDecoration(
          color: Colors.white,
          border: Border(top: BorderSide(color: Color(0xFFE6ECF4)))),
      child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            child: Row(children: [
              item(
                  'Home',
                  home ? Icons.home_rounded : Icons.home_outlined,
                  onHome ??
                      () => Navigator.of(context).popUntil((route) =>
                          route.settings.name == 'transport-home' ||
                          route.isFirst),
                  home && !profile),
              item('Profile',
                  profile ? Icons.person_rounded : Icons.person_outline_rounded,
                  () {
                if (!profile) {
                  openScreen(context, const ProfileScreen(), name: 'profile');
                }
              }, profile),
              if (onSwitch != null)
                item('Sign out', Icons.logout_rounded, onSwitch, false)
              else
                item(
                    'Back',
                    Icons.arrow_back_rounded,
                    Navigator.of(context).canPop()
                        ? () => Navigator.of(context).maybePop()
                        : null,
                    false),
            ]),
          )),
    );
  }
}

class ProfileAvatar extends StatelessWidget {
  const ProfileAvatar({super.key, this.driver = false});
  final bool driver;
  @override
  Widget build(BuildContext context) => Container(
        width: 76,
        height: 76,
        decoration: BoxDecoration(
            gradient: busSoftGradient,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: const Color(0xFFDCE8FA))),
        child: Icon(
            driver ? Icons.directions_bus_rounded : Icons.person_rounded,
            color: busBlue,
            size: 38),
      );
}

/// The Figma map artwork is a preview, not a live location feed.
class BusMapPreview extends StatelessWidget {
  const BusMapPreview(
      {super.key, this.height = 174, this.radius = 20, this.onTap});
  final double height;
  final double radius;
  final VoidCallback? onTap;
  @override
  Widget build(BuildContext context) => Semantics(
      label: 'Bus route preview',
      button: onTap != null,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: BusCard(
            radius: radius,
            padding: const EdgeInsets.all(9),
            child: SizedBox(
                height: height,
                width: double.infinity,
                child: Stack(children: [
                  Positioned.fill(
                      child: Image.asset('assets/figma/767fa.png',
                          fit: BoxFit.cover)),
                  Positioned(
                      left: 86,
                      top: 32,
                      child: Container(
                          width: 48,
                          height: 55,
                          decoration: BoxDecoration(
                              color: busBlue,
                              borderRadius: BorderRadius.circular(28),
                              boxShadow: const [
                                BoxShadow(
                                    color: Color(0x33000000),
                                    blurRadius: 4,
                                    offset: Offset(0, 4))
                              ]),
                          child: const Center(
                              child: DesignAsset('d6e2b.svg',
                                  width: 28, height: 28)))),
                ]))),
      ));
}

class DetailField extends StatelessWidget {
  const DetailField(this.label, this.value, {super.key});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label,
            style: const TextStyle(
                fontSize: 12, fontWeight: FontWeight.bold, color: busMuted)),
        const SizedBox(height: 5),
        Text(value, style: const TextStyle(fontSize: 14, color: busText)),
      ]));
}

class HomeHeader extends StatelessWidget {
  const HomeHeader(
      {super.key,
      required this.details,
      required this.action,
      this.driver = false});
  final Widget details, action;
  final bool driver;
  @override
  Widget build(BuildContext context) => Column(children: [
        Container(
          padding: EdgeInsets.fromLTRB(
              24, MediaQuery.paddingOf(context).top + 16, 24, 28),
          decoration: const BoxDecoration(
              gradient: busGradient,
              borderRadius: BorderRadius.vertical(bottom: Radius.circular(32))),
          child: Column(children: [
            Row(children: [
              const Icon(Icons.directions_bus_rounded,
                  color: Colors.white, size: 26),
              const SizedBox(width: 10),
              Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    const Text('School Bus',
                        style: TextStyle(
                            color: Colors.white,
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            letterSpacing: -0.5)),
                    Text(
                        driver
                            ? 'Your route. Your day.'
                            : 'Every journey, connected.',
                        style: const TextStyle(
                            color: Color(0xFFD7E8FF), fontSize: 12)),
                  ])),
              IconButtonTheme(
                  data: IconButtonThemeData(
                      style: IconButton.styleFrom(
                          foregroundColor: Colors.white,
                          backgroundColor: const Color(0x22FFFFFF))),
                  child: action),
            ]),
            const SizedBox(height: 24),
            BusCard(
                padding: const EdgeInsets.all(20),
                child: Row(children: [
                  ProfileAvatar(driver: driver),
                  const SizedBox(width: 16),
                  Expanded(child: details),
                ])),
          ]),
        ),
        const SizedBox(height: 24),
      ]);
}
