import 'package:flutter/material.dart';
import '../../core/bus_ui.dart';

class MapScreen extends StatelessWidget {
  const MapScreen({super.key, this.driver = false});
  final bool driver;
  @override
  Widget build(BuildContext context) => BusScaffold(
      title: driver ? 'Route Preview' : 'School Bus Locator',
      padding: const EdgeInsets.symmetric(horizontal: 39, vertical: 32),
      child: Column(children: [
        BusCard(
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 32),
            child: Row(children: [
              const SizedBox(
                  width: 51,
                  height: 47,
                  child: Stack(alignment: Alignment.center, children: [
                    DesignAsset('dd7f5.svg', width: 51, height: 47),
                    DesignAsset('05112.svg', width: 37, height: 38)
                  ])),
              const SizedBox(width: 16),
              Expanded(
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                    const Text('Royal College',
                        style: TextStyle(
                            fontSize: 16,
                            color: Colors.black,
                            fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                            color: busBlue,
                            borderRadius: BorderRadius.circular(8)),
                        child: const Text('Arriving at school · 2 mins',
                            style: TextStyle(
                                color: Colors.white,
                                fontSize: 13,
                                fontWeight: FontWeight.bold))),
                  ]))
            ])),
        const SizedBox(height: 24),
        ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: SizedBox(
                height: 450,
                width: double.infinity,
                child: Stack(children: [
                  Positioned.fill(
                      child: Image.asset('assets/figma/767fa.png',
                          fit: BoxFit.cover)),
                  Positioned(
                      top: 4,
                      left: 112,
                      child: Container(
                          width: 56,
                          height: 56,
                          decoration: BoxDecoration(
                              color: busBlue,
                              borderRadius: BorderRadius.circular(28)),
                          child: const Center(
                              child: DesignAsset('d6e2b.svg',
                                  width: 28, height: 28)))),
                  const Positioned(
                      top: 51,
                      left: 159,
                      child: DesignAsset('f4c5e.svg', width: 47, height: 118)),
                  const Positioned(
                      top: 167,
                      left: 183,
                      child: DesignAsset('e131b.svg', width: 55, height: 51)),
                  const Positioned(
                      top: 176,
                      left: 195,
                      child: DesignAsset('5898c.svg', width: 31, height: 29)),
                ]))),
        const SizedBox(height: 16),
        const Text('Sample route preview · not a live location',
            style: TextStyle(fontSize: 12, color: busMuted)),
      ]));
}
