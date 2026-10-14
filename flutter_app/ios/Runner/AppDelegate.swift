import Flutter
import UIKit
import GoogleMaps

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  private var mapsConfigured = false
  private var mapsConfigurationChannel: FlutterMethodChannel?
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    if let key = Bundle.main.object(forInfoDictionaryKey: "GoogleMapsAPIKey") as? String,
       !key.isEmpty, !key.hasPrefix("$(") {
      mapsConfigured = GMSServices.provideAPIKey(key)
    }
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "MapsConfiguration") {
      let channel = FlutterMethodChannel(
        name: "school_bus/maps_configuration",
        binaryMessenger: registrar.messenger()
      )
      channel.setMethodCallHandler { [weak self] call, result in
        if call.method == "isConfigured" {
          result(self?.mapsConfigured ?? false)
        } else {
          result(FlutterMethodNotImplemented)
        }
      }
      mapsConfigurationChannel = channel
    }
  }
}
