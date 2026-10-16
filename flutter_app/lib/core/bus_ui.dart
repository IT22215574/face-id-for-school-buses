import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import '../features/profile/profile_screen.dart';

const busBlue = Color(0xFF1A73E8);
const busBackground = Color(0xFFF5F5F5);
const busText = Color(0xFF5E5757);
const busMuted = Color(0xFF78766E);

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
            borderRadius: BorderRadius.circular(radius),
            boxShadow: const [
              BoxShadow(
                  color: Color(0x33000000), blurRadius: 4, offset: Offset(0, 3))
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
            toolbarHeight: 100,
            shape: const RoundedRectangleBorder(
                borderRadius:
                    BorderRadius.vertical(bottom: Radius.circular(20)))),
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
  Widget build(BuildContext context) => Material(
        color: Colors.white,
        elevation: 8,
        child: SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              child: Row(children: [
                Expanded(
                    child: TextButton.icon(
                        onPressed: onHome ??
                            () => Navigator.of(context).popUntil((route) =>
                                route.settings.name == 'transport-home' ||
                                route.isFirst),
                        icon: const Icon(Icons.home_rounded),
                        label: const Text('Home'))),
                Expanded(
                    child: TextButton.icon(
                        onPressed: () {
                          if (ModalRoute.of(context)?.settings.name ==
                              'profile') {
                            return;
                          }
                          openScreen(context, const ProfileScreen(),
                              name: 'profile');
                        },
                        icon: const Icon(Icons.account_circle_outlined),
                        label: const Text('Profile'))),
                if (onSwitch != null)
                  Expanded(
                      child: Tooltip(
                          message: 'Sign out',
                          child: TextButton.icon(
                              onPressed: onSwitch,
                              icon: const Icon(Icons.logout),
                              label: const Text('Sign out'))))
                else
                  Expanded(
                      child: TextButton.icon(
                          onPressed: Navigator.of(context).canPop()
                              ? () => Navigator.of(context).maybePop()
                              : null,
                          icon: const Icon(Icons.arrow_back),
                          label: const Text('Back'))),
              ]),
            )),
      );
}

class ProfileAvatar extends StatelessWidget {
  const ProfileAvatar({super.key, this.driver = false});
  final bool driver;
  @override
  Widget build(BuildContext context) => SizedBox(
      width: 82,
      height: 81,
      child: Stack(alignment: Alignment.center, children: [
        const DesignAsset('2e094.svg', width: 82, height: 81),
        DesignAsset(driver ? '3c218.svg' : '3a794.svg',
            width: driver ? 60 : 62, height: 61),
      ]));
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
  Widget build(BuildContext context) => Stack(children: [
        Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: Container(
                height: 210,
                decoration: const BoxDecoration(
                    color: busBlue,
                    borderRadius:
                        BorderRadius.vertical(bottom: Radius.circular(20)),
                    boxShadow: [
                      BoxShadow(
                          color: Color(0x33000000),
                          blurRadius: 4,
                          offset: Offset(0, 4))
                    ]))),
        Column(children: [
          SizedBox(
              height: 80 + MediaQuery.paddingOf(context).top,
              child: Align(
                  alignment: Alignment.topRight,
                  child: Padding(
                      padding: EdgeInsets.only(
                          top: 28 + MediaQuery.paddingOf(context).top,
                          right: 24),
                      child: action))),
          Padding(
              padding: EdgeInsets.symmetric(
                  horizontal: MediaQuery.sizeOf(context).width < 370 ? 24 : 42),
              child: BusCard(
                  padding: const EdgeInsets.all(24),
                  child: ConstrainedBox(
                      constraints: const BoxConstraints(minHeight: 108),
                      child: Row(children: [
                        ProfileAvatar(driver: driver),
                        const SizedBox(width: 20),
                        Expanded(child: details)
                      ])))),
          const SizedBox(height: 17),
        ]),
      ]);
}
