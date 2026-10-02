import 'package:flutter/material.dart';

class ChildDetailScreen extends StatelessWidget {
  const ChildDetailScreen({super.key, required this.studentName});

  final String studentName;

  @override
  Widget build(BuildContext context) {
    final timeline = [
      _TimelineItem(title: 'Boarded Bus', subtitle: '7:42 AM · Route 24', isPositive: true),
      _TimelineItem(title: 'Bus departed school', subtitle: '7:45 AM · North Loop', isPositive: false),
      _TimelineItem(title: 'Arrived home stop', subtitle: '8:12 AM · 38th Street', isPositive: false),
    ];

    return Scaffold(
      appBar: AppBar(title: Text(studentName)),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Card(
              child: ListTile(
                title: const Text('Latest status'),
                subtitle: Text('$studentName is currently ON_BUS'),
                trailing: const Icon(Icons.check_circle, color: Colors.green),
              ),
            ),
            const SizedBox(height: 16),
            const Text('Timeline', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            Expanded(
              child: ListView.separated(
                itemCount: timeline.length,
                separatorBuilder: (_, __) => const Divider(),
                itemBuilder: (context, index) => timeline[index],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _TimelineItem extends StatelessWidget {
  const _TimelineItem({required this.title, required this.subtitle, required this.isPositive});

  final String title;
  final String subtitle;
  final bool isPositive;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: isPositive ? Colors.green.shade100 : Colors.orange.shade100,
        child: Icon(isPositive ? Icons.boarding : Icons.home, color: isPositive ? Colors.green : Colors.orange),
      ),
      title: Text(title),
      subtitle: Text(subtitle),
    );
  }
}
